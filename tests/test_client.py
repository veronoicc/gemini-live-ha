"""Tests for Gemini Live client."""

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
