"""Tests for Gemini Live client."""

import asyncio
import base64
import json
import struct
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from custom_components.gemini_live_ha.client import GeminiLiveClient, pcm_to_wav
from custom_components.gemini_live_ha.const import (
    CONF_API_KEY,
    CONF_EXPOSE_HA_CONTROL,
    CONF_GOOGLE_SEARCH,
    CONF_MODEL,
    CONF_SYSTEM_INSTRUCTION,
    CONF_TEMPERATURE,
    CONF_THINKING_LEVEL,
    CONF_VOICE,
    DEFAULT_MODEL,
    MODEL_3_8_LIVE_EXTENDED_THINKING,
    THINKING_LEVEL_HIGH,
    VOICE_FENRIR,
)


def test_pcm_to_wav_header() -> None:
    """Test converting raw PCM into a standard WAV header."""
    raw_pcm = b"\x00\x00" * 24000  # 1 second of 24kHz 16-bit mono silence
    wav_data = pcm_to_wav(raw_pcm, sample_rate=24000)

    # Check WAV RIFF header
    assert wav_data[:4] == b"RIFF"
    assert wav_data[8:12] == b"WAVE"
    assert wav_data[12:16] == b"fmt "

    # Check sample rate at offset 24 (little-endian 32-bit int)
    sample_rate = struct.unpack("<I", wav_data[24:28])[0]
    assert sample_rate == 24000

    # Check channels at offset 22 (little-endian 16-bit int)
    channels = struct.unpack("<H", wav_data[22:24])[0]
    assert channels == 1

    # Check data subchunk
    data_index = wav_data.find(b"data")
    assert data_index != -1
    data_size = struct.unpack("<I", wav_data[data_index + 4 : data_index + 8])[0]
    assert data_size == len(raw_pcm)


def test_build_setup_message_defaults() -> None:
    """Test setup message with default parameters."""
    hass = MagicMock()
    config = {
        CONF_API_KEY: "test_key",
        CONF_MODEL: DEFAULT_MODEL,
        CONF_VOICE: VOICE_FENRIR,
        CONF_TEMPERATURE: 0.8,
        CONF_SYSTEM_INSTRUCTION: "Custom instructions.",
        CONF_GOOGLE_SEARCH: False,
        CONF_EXPOSE_HA_CONTROL: True,
    }
    client = GeminiLiveClient(hass, config)
    setup = client._build_setup_message()

    s = setup["setup"]
    assert s["model"] == f"models/{DEFAULT_MODEL}"
    assert s["generationConfig"]["temperature"] == 0.8
    assert (
        s["generationConfig"]["speechConfig"]["voiceConfig"]["prebuiltVoiceConfig"][
            "voiceName"
        ]
        == VOICE_FENRIR
    )
    assert s["systemInstruction"]["parts"][0]["text"] == "Custom instructions."
    assert "tools" in s
    assert any("functionDeclarations" in t for t in s["tools"])


def test_build_setup_message_thinking_and_search() -> None:
    """Test setup message with thinking level and Google Search."""
    hass = MagicMock()
    config = {
        CONF_API_KEY: "test_key",
        CONF_MODEL: MODEL_3_8_LIVE_EXTENDED_THINKING,
        CONF_THINKING_LEVEL: THINKING_LEVEL_HIGH,
        CONF_GOOGLE_SEARCH: True,
        CONF_EXPOSE_HA_CONTROL: False,
    }
    client = GeminiLiveClient(hass, config)
    setup = client._build_setup_message()

    s = setup["setup"]
    assert s["generationConfig"]["thinkingConfig"]["thinkingLevel"] == "HIGH"
    assert any("googleSearch" in t for t in s["tools"])


def test_tools_mutual_exclusivity() -> None:
    """Test that Google Search and HA control cannot both be sent."""
    hass = MagicMock()
    config = {
        CONF_API_KEY: "test_key",
        CONF_MODEL: DEFAULT_MODEL,
        CONF_GOOGLE_SEARCH: True,
        CONF_EXPOSE_HA_CONTROL: True,
    }
    client = GeminiLiveClient(hass, config)
    setup = client._build_setup_message()
    tools = setup["setup"].get("tools", [])
    has_search = any("googleSearch" in t for t in tools)
    has_funcs = any("functionDeclarations" in t for t in tools)
    assert not (has_search and has_funcs)


@pytest.mark.asyncio
async def test_execute_ha_command() -> None:
    """Test executing Home Assistant command."""
    hass = MagicMock()
    config = {CONF_API_KEY: "test_key"}
    client = GeminiLiveClient(hass, config)

    mock_result = MagicMock()
    mock_result.response.speech = {"plain": {"speech": "Turned on the lamp."}}

    with patch(
        "homeassistant.components.conversation.async_converse",
        new_callable=AsyncMock,
        return_value=mock_result,
    ) as mock_converse:
        result = await client._execute_ha_command("turn on the lamp")
        assert result == "Turned on the lamp."
        mock_converse.assert_called_once()


@pytest.mark.asyncio
async def test_process_audio_turn() -> None:
    """Test streaming audio turn to Gemini Live WebSocket."""
    hass = MagicMock()
    config = {CONF_API_KEY: "test_key", CONF_MODEL: DEFAULT_MODEL}
    client = GeminiLiveClient(hass, config)

    encoded_audio = base64.b64encode(b"output_pcm_audio").decode("utf-8")
    server_messages = [
        json.dumps({"setupComplete": {}}),
        json.dumps(
            {
                "serverContent": {
                    "inputTranscription": {"text": "Schalte das Licht an"},
                    "outputTranscription": {"text": "Licht eingeschaltet"},
                    "modelTurn": {"parts": [{"inlineData": {"data": encoded_audio}}]},
                    "turnComplete": True,
                }
            }
        ),
    ]

    sent_messages: list[str] = []

    class MockWebSocket:
        def __init__(self) -> None:
            self.close_code = 1000
            self.close_reason = "OK"
            self.queue: asyncio.Queue[str] = asyncio.Queue()
            for m in server_messages:
                self.queue.put_nowait(m)

        async def send(self, msg: str) -> None:
            sent_messages.append(msg)

        def __aiter__(self):
            return self

        async def __anext__(self):
            if self.queue.empty():
                raise StopAsyncIteration
            await asyncio.sleep(0.001)
            return await self.queue.get()

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    async def mock_audio_stream():
        yield b"chunk_1"
        yield b"chunk_2"

    mock_ws = MockWebSocket()
    with patch("websockets.connect", return_value=mock_ws) as mock_connect:
        user_text, model_text, audio = await client.process_audio_turn(
            mock_audio_stream()
        )
        assert user_text == "Schalte das Licht an"
        assert model_text == "Licht eingeschaltet"
        assert audio == b"output_pcm_audio"

        # Verify connect called with ssl context
        mock_connect.assert_called_once()
        assert "ssl" in mock_connect.call_args.kwargs
        assert mock_connect.call_args.kwargs["ssl"] is not None

        # Verify setup message sent first
        assert len(sent_messages) >= 3
        setup_parsed = json.loads(sent_messages[0])
        assert "setup" in setup_parsed

        # Verify audio chunks sent
        assert any(
            "realtimeInput" in m and "audio" in json.loads(m)["realtimeInput"]
            for m in sent_messages
        )

        # Verify audioStreamEnd sent
        assert any(
            json.loads(m).get("realtimeInput", {}).get("audioStreamEnd") is True
            for m in sent_messages
        )


@pytest.mark.asyncio
async def test_process_text_turn() -> None:
    """Test sending text turn to Gemini Live WebSocket."""
    hass = MagicMock()
    config = {CONF_API_KEY: "test_key", CONF_MODEL: DEFAULT_MODEL}
    client = GeminiLiveClient(hass, config)

    encoded_audio = base64.b64encode(b"reply_pcm_audio").decode("utf-8")
    server_messages = [
        json.dumps({"setupComplete": {}}),
        json.dumps(
            {
                "serverContent": {
                    "outputTranscription": {"text": "Hallo! Wie kann ich helfen?"},
                    "modelTurn": {"parts": [{"inlineData": {"data": encoded_audio}}]},
                    "turnComplete": True,
                }
            }
        ),
    ]

    sent_messages: list[str] = []

    class MockWebSocket:
        def __init__(self) -> None:
            self.close_code = 1000
            self.close_reason = "OK"
            self.queue: asyncio.Queue[str] = asyncio.Queue()
            for m in server_messages:
                self.queue.put_nowait(m)

        async def send(self, msg: str) -> None:
            sent_messages.append(msg)

        def __aiter__(self):
            return self

        async def __anext__(self):
            if self.queue.empty():
                raise StopAsyncIteration
            return await self.queue.get()

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    mock_ws = MockWebSocket()
    with patch("websockets.connect", return_value=mock_ws) as mock_connect:
        model_text, audio = await client.process_text_turn("Hallo Gemini")
        assert model_text == "Hallo! Wie kann ich helfen?"
        assert audio == b"reply_pcm_audio"

        mock_connect.assert_called_once()
        assert "ssl" in mock_connect.call_args.kwargs
        assert len(sent_messages) == 2
        # setup message
        assert "setup" in json.loads(sent_messages[0])
        # clientContent
        client_content = json.loads(sent_messages[1])
        assert "clientContent" in client_content
        assert (
            client_content["clientContent"]["turns"][0]["parts"][0]["text"]
            == "Hallo Gemini"
        )
