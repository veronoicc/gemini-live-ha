"""Client for interacting with the Gemini Live WebSocket API."""

from __future__ import annotations

import asyncio
import base64
import contextlib
import io
import json
import logging
import wave
from collections.abc import AsyncIterable
from typing import Any

import websockets
from homeassistant.components import conversation
from homeassistant.core import Context, HomeAssistant
from homeassistant.util.ssl import get_default_context

from .const import (
    CHANNELS,
    CONF_API_KEY,
    CONF_EXPOSE_HA_CONTROL,
    CONF_GOOGLE_SEARCH,
    CONF_MODEL,
    CONF_SYSTEM_INSTRUCTION,
    CONF_TEMPERATURE,
    CONF_THINKING_LEVEL,
    CONF_TOOL_MODE,
    CONF_VOICE,
    DEFAULT_EXPOSE_HA_CONTROL,
    DEFAULT_MODEL,
    DEFAULT_SYSTEM_INSTRUCTION,
    DEFAULT_TEMPERATURE,
    DEFAULT_THINKING_LEVEL,
    DEFAULT_VOICE,
    GEMINI_LIVE_WS_ENDPOINT,
    MODEL_3_8_LIVE,
    MODEL_3_8_LIVE_EXTENDED_THINKING,
    OUTPUT_SAMPLE_RATE,
    SAMPLE_WIDTH,
    THINKING_LEVEL_OFF,
    TOOL_MODE_GOOGLE_SEARCH,
    TOOL_MODE_HA_CONTROL,
    TOOL_MODE_NONE,
)

_LOGGER = logging.getLogger(__name__)


def pcm_to_wav(
    pcm_bytes: bytes,
    sample_rate: int = OUTPUT_SAMPLE_RATE,
    channels: int = CHANNELS,
    sample_width: int = SAMPLE_WIDTH,
) -> bytes:
    """Pack raw 16-bit PCM bytes into a standard WAV container."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_bytes)
    return buf.getvalue()


class GeminiLiveClient:
    """Manages real-time bidirectional streaming with Gemini Live API."""

    def __init__(self, hass: HomeAssistant, config: dict[str, Any]) -> None:
        """Initialize client with configuration."""
        self.hass = hass
        self.config = config

    @property
    def api_key(self) -> str:
        """Return configured API key."""
        return self.config[CONF_API_KEY]

    @property
    def model(self) -> str:
        """Return configured model."""
        return self.config.get(CONF_MODEL, DEFAULT_MODEL)

    @property
    def voice(self) -> str:
        """Return configured voice."""
        return self.config.get(CONF_VOICE, DEFAULT_VOICE)

    @property
    def system_instruction(self) -> str:
        """Return configured system instruction."""
        return self.config.get(CONF_SYSTEM_INSTRUCTION, DEFAULT_SYSTEM_INSTRUCTION)

    @property
    def temperature(self) -> float:
        """Return configured temperature."""
        return float(self.config.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE))

    @property
    def thinking_level(self) -> str:
        """Return configured thinking level."""
        return self.config.get(CONF_THINKING_LEVEL, DEFAULT_THINKING_LEVEL)

    @property
    def tool_mode(self) -> str:
        """Return configured tool mode."""
        if mode := self.config.get(CONF_TOOL_MODE):
            return mode
        if self.config.get(CONF_GOOGLE_SEARCH):
            return TOOL_MODE_GOOGLE_SEARCH
        if self.config.get(CONF_EXPOSE_HA_CONTROL, DEFAULT_EXPOSE_HA_CONTROL):
            return TOOL_MODE_HA_CONTROL
        return TOOL_MODE_NONE

    def _build_setup_message(self) -> dict[str, Any]:
        """Build initial session setup message."""
        gen_config: dict[str, Any] = {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {
                        "voiceName": self.voice,
                    }
                }
            },
            "temperature": self.temperature,
        }

        # Thinking config if supported and enabled
        if self.thinking_level != THINKING_LEVEL_OFF and self.model != MODEL_3_8_LIVE:
            gen_config["thinkingConfig"] = {
                "thinkingLevel": self.thinking_level.upper()
            }

        tools: list[dict[str, Any]] = []
        # Google Search and custom function calling are mutually exclusive in Gemini Live API
        if self.tool_mode == TOOL_MODE_GOOGLE_SEARCH:
            tools.append({"googleSearch": {}})
        elif self.tool_mode == TOOL_MODE_HA_CONTROL:
            func_decl: dict[str, Any] = {
                "name": "control_home_assistant",
                "description": (
                    "Execute smart home commands or query device states in Home Assistant "
                    "(e.g., 'turn off living room light', 'what is the temperature')."
                ),
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "command": {
                            "type": "STRING",
                            "description": "Natural language smart home command or query.",
                        }
                    },
                    "required": ["command"],
                },
            }
            if self.model == MODEL_3_8_LIVE_EXTENDED_THINKING:
                func_decl["behavior"] = "NON_BLOCKING"
            tools.append({"functionDeclarations": [func_decl]})

        setup: dict[str, Any] = {
            "model": f"models/{self.model}",
            "generationConfig": gen_config,
            "systemInstruction": {
                "parts": [{"text": self.system_instruction}],
            },
            "inputAudioTranscription": {},
            "outputAudioTranscription": {},
        }

        if tools:
            setup["tools"] = tools

        return {"setup": setup}

    async def _execute_ha_command(
        self, command: str, context: Context | None = None
    ) -> str:
        """Execute command in Home Assistant using conversation agent."""
        try:
            _LOGGER.debug("Executing HA command: %s", command)
            result = await conversation.async_converse(
                self.hass,
                text=command,
                conversation_id=None,
                context=context,
            )
            response_speech = (
                result.response.speech.get("plain", {}).get("speech")
                if result.response and result.response.speech
                else None
            )
            return response_speech or "Action completed."
        except Exception as err:  # noqa: BLE001
            _LOGGER.error(
                "Error executing Home Assistant command '%s': %s", command, err
            )
            return f"Error executing command: {err}"

    async def _handle_tool_call(
        self,
        ws: websockets.WebSocketClientProtocol,
        tool_call: dict[str, Any],
        context: Context | None,
    ) -> None:
        """Handle incoming tool calls from Gemini."""
        function_responses: list[dict[str, Any]] = []
        for fc in tool_call.get("functionCalls", []):
            name = fc.get("name")
            call_id = fc.get("id")
            args = fc.get("args", {})
            if name == "control_home_assistant":
                command = args.get("command", "")
                result_text = await self._execute_ha_command(command, context)
                function_responses.append(
                    {
                        "name": name,
                        "id": call_id,
                        "response": {"result": result_text},
                    }
                )
            else:
                function_responses.append(
                    {
                        "name": name,
                        "id": call_id,
                        "response": {"error": f"Unknown tool: {name}"},
                    }
                )

        response_msg = {
            "toolResponse": {
                "functionResponses": function_responses,
            }
        }
        await ws.send(json.dumps(response_msg))
        _LOGGER.debug("Sent tool response for %d call(s)", len(function_responses))

    async def process_audio_turn(
        self, audio_stream: AsyncIterable[bytes], context: Context | None = None
    ) -> tuple[str, str, bytes]:
        """Stream user audio to Gemini Live and return (user_text, model_text, audio_pcm)."""
        ws_url = f"{GEMINI_LIVE_WS_ENDPOINT}?key={self.api_key}"

        user_text_parts: list[str] = []
        interim_user_text: str = ""
        model_text_parts: list[str] = []
        audio_chunks: list[bytes] = []

        ssl_context = get_default_context()

        async with websockets.connect(
            ws_url, ssl=ssl_context, ping_interval=20, ping_timeout=20
        ) as ws:
            # 1. Send setup message
            setup_msg = self._build_setup_message()
            await ws.send(json.dumps(setup_msg))
            _LOGGER.debug("Sent Live API setup message for model: %s", self.model)

            # 2. Wait for setupComplete from server before sending any realtimeInput
            setup_complete = False
            async for raw_message in ws:
                try:
                    data = json.loads(raw_message)
                except json.JSONDecodeError:
                    continue

                if "setupComplete" in data:
                    setup_complete = True
                    _LOGGER.debug("Gemini Live session setupComplete confirmed")
                    break

                if "error" in data:
                    _LOGGER.error("Gemini Live API setup error: %s", data["error"])
                    return "", "", b""

            if not setup_complete:
                _LOGGER.error(
                    "Gemini Live WebSocket closed before setupComplete: code=%s, reason=%s",
                    ws.close_code,
                    ws.close_reason,
                )
                return "", "", b""

            # 3. Audio streaming task
            async def send_audio() -> None:
                """Stream input audio chunks to WebSocket."""
                try:
                    chunks_sent = 0
                    total_bytes = 0
                    async for chunk in audio_stream:
                        if not chunk:
                            continue
                        chunks_sent += 1
                        total_bytes += len(chunk)
                        encoded = base64.b64encode(chunk).decode("utf-8")
                        msg = {
                            "realtimeInput": {
                                "audio": {
                                    "mimeType": "audio/pcm;rate=16000",
                                    "data": encoded,
                                }
                            }
                        }
                        await ws.send(json.dumps(msg))

                    _LOGGER.debug(
                        "Streamed %d audio chunks (%d bytes), sending audioStreamEnd",
                        chunks_sent,
                        total_bytes,
                    )
                    # Indicate end of audio stream to Gemini Live
                    await ws.send(
                        json.dumps({"realtimeInput": {"audioStreamEnd": True}})
                    )
                except Exception as err:  # noqa: BLE001
                    _LOGGER.warning("Exception in send_audio: %s", err)

            send_task = asyncio.create_task(send_audio())

            # 4. Receive model responses
            try:
                async for message in ws:
                    try:
                        data = json.loads(message)
                    except json.JSONDecodeError:
                        continue

                    if "error" in data:
                        _LOGGER.error("Gemini Live API error: %s", data["error"])
                        break

                    # Tool calls
                    if "toolCall" in data:
                        await self._handle_tool_call(ws, data["toolCall"], context)

                    # Server content
                    if "serverContent" in data:
                        server_content = data["serverContent"]

                        # User speech transcription
                        if "inputTranscription" in server_content:
                            text = server_content["inputTranscription"].get("text", "")
                            if text:
                                user_text_parts.append(text)
                        elif "interimInputTranscription" in server_content:
                            text = server_content["interimInputTranscription"].get(
                                "text", ""
                            )
                            if text:
                                interim_user_text = text

                        # Model speech transcription
                        if "outputTranscription" in server_content:
                            text = server_content["outputTranscription"].get("text", "")
                            if text:
                                model_text_parts.append(text)

                        # Model audio output and potential text parts
                        model_turn = server_content.get("modelTurn")
                        if model_turn and "parts" in model_turn:
                            for part in model_turn["parts"]:
                                if part.get("text"):
                                    model_text_parts.append(part["text"])
                                inline_data = part.get("inlineData")
                                if inline_data and "data" in inline_data:
                                    raw_pcm = base64.b64decode(inline_data["data"])
                                    audio_chunks.append(raw_pcm)

                        # Check turn completion
                        if server_content.get("turnComplete"):
                            _LOGGER.debug("Received turnComplete from server")
                            status = server_content.get("interactionStatus")
                            if status != "IN_PROGRESS":
                                break

                    # GoAway warning
                    if "goAway" in data:
                        _LOGGER.warning(
                            "Gemini Live server sent goAway: %s", data["goAway"]
                        )
                        break
            finally:
                if not send_task.done():
                    send_task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await send_task

            if ws.close_code is not None and ws.close_code != 1000:
                _LOGGER.warning(
                    "Gemini Live WebSocket closed with code %s: %s",
                    ws.close_code,
                    ws.close_reason,
                )

        user_text = "".join(user_text_parts).strip()
        if not user_text and interim_user_text:
            user_text = interim_user_text.strip()
        model_text = "".join(model_text_parts).strip()
        audio_pcm = b"".join(audio_chunks)

        _LOGGER.debug(
            "Completed audio turn. User: '%s', Model: '%s', Audio bytes: %d",
            user_text,
            model_text,
            len(audio_pcm),
        )
        return user_text, model_text, audio_pcm

    async def process_text_turn(
        self, text: str, context: Context | None = None
    ) -> tuple[str, bytes]:
        """Send text input to Gemini Live and return (model_text, audio_pcm)."""
        ws_url = f"{GEMINI_LIVE_WS_ENDPOINT}?key={self.api_key}"

        model_text_parts: list[str] = []
        audio_chunks: list[bytes] = []

        ssl_context = get_default_context()

        async with websockets.connect(
            ws_url, ssl=ssl_context, ping_interval=20, ping_timeout=20
        ) as ws:
            # 1. Send setup message
            setup_msg = self._build_setup_message()
            await ws.send(json.dumps(setup_msg))

            # 2. Wait for setupComplete
            setup_complete = False
            async for raw_msg in ws:
                try:
                    data = json.loads(raw_msg)
                except json.JSONDecodeError:
                    continue

                if "setupComplete" in data:
                    setup_complete = True
                    break

                if "error" in data:
                    _LOGGER.error("Gemini Live API setup error: %s", data["error"])
                    return "", b""

            if not setup_complete:
                _LOGGER.error(
                    "Gemini Live WebSocket closed before setupComplete: code=%s, reason=%s",
                    ws.close_code,
                    ws.close_reason,
                )
                return "", b""

            # 3. Send client content turn
            client_msg = {
                "clientContent": {
                    "turns": [
                        {
                            "role": "user",
                            "parts": [{"text": text}],
                        }
                    ],
                    "turnComplete": True,
                }
            }
            await ws.send(json.dumps(client_msg))

            # 4. Receive model response
            async for message in ws:
                try:
                    data = json.loads(message)
                except json.JSONDecodeError:
                    continue

                if "error" in data:
                    _LOGGER.error("Gemini Live API error: %s", data["error"])
                    break

                if "toolCall" in data:
                    await self._handle_tool_call(ws, data["toolCall"], context)

                if "serverContent" in data:
                    server_content = data["serverContent"]

                    if "outputTranscription" in server_content:
                        t = server_content["outputTranscription"].get("text", "")
                        if t:
                            model_text_parts.append(t)

                    model_turn = server_content.get("modelTurn")
                    if model_turn and "parts" in model_turn:
                        for part in model_turn["parts"]:
                            if part.get("text"):
                                model_text_parts.append(part["text"])
                            inline_data = part.get("inlineData")
                            if inline_data and "data" in inline_data:
                                raw_pcm = base64.b64decode(inline_data["data"])
                                audio_chunks.append(raw_pcm)

                    if server_content.get("turnComplete"):
                        status = server_content.get("interactionStatus")
                        if status != "IN_PROGRESS":
                            break

            if ws.close_code is not None and ws.close_code != 1000:
                _LOGGER.warning(
                    "Gemini Live WebSocket closed with code %s: %s",
                    ws.close_code,
                    ws.close_reason,
                )
        model_text = "".join(model_text_parts).strip()
        audio_pcm = b"".join(audio_chunks)

        return model_text, audio_pcm

    async def generate_tts_audio(self, message: str) -> bytes:
        """Generate spoken WAV audio for a message."""
        prompt = f"Please read the following message aloud clearly: {message}"
        _, audio_pcm = await self.process_text_turn(prompt)
        return pcm_to_wav(audio_pcm)
