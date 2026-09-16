"""Tests for Gemini Live STT, Conversation, and TTS entities."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from custom_components.gemini_live_ha import GeminiLiveRuntimeData
from custom_components.gemini_live_ha.conversation import GeminiLiveConversationEntity
from custom_components.gemini_live_ha.stt import GeminiLiveSTTEntity
from custom_components.gemini_live_ha.tts import GeminiLiveTTSEntity
from custom_components.gemini_live_ha.turn_cache import TurnCache
from homeassistant.components.conversation import ConversationInput
from homeassistant.components.stt import (
    AudioCodecs,
    AudioFormats,
    SpeechResultState,
)
from homeassistant.config_entries import ConfigEntry


@pytest.fixture
def mock_entry() -> ConfigEntry:
    """Create a mock ConfigEntry with runtime data."""
    entry = ConfigEntry(
        entry_id="test_entry_id",
        title="Gemini Live (gemini-3.8-live)",
        data={"api_key": "test_key", "model": "gemini-3.8-live"},
    )
    client = MagicMock()
    turn_cache = TurnCache(ttl=60)
    entry.runtime_data = GeminiLiveRuntimeData(
        client=client,
        turn_cache=turn_cache,
        options={},
    )
    return entry


@pytest.mark.asyncio
async def test_stt_entity(mock_entry: ConfigEntry) -> None:
    """Test STT entity processing."""
    stt_entity = GeminiLiveSTTEntity(mock_entry)

    assert stt_entity.supported_formats == [AudioFormats.WAV]
    assert stt_entity.supported_codecs == [AudioCodecs.PCM]
    assert "en" in stt_entity.supported_languages

    # Mock client.process_audio_turn
    mock_entry.runtime_data.client.process_audio_turn = AsyncMock(
        return_value=("What is the weather?", "It is sunny.", b"audio_pcm_24k")
    )

    metadata = MagicMock()

    async def dummy_stream():
        yield b"chunk"

    result = await stt_entity.async_process_audio_stream(metadata, dummy_stream())
    assert result.result == SpeechResultState.SUCCESS
    assert result.text == "What is the weather?"

    # Check that turn_cache stored the turn
    cached = mock_entry.runtime_data.turn_cache.pop_turn("What is the weather?")
    assert cached is not None
    assert cached[0] == "It is sunny."
    assert cached[1] == b"audio_pcm_24k"


@pytest.mark.asyncio
async def test_conversation_entity_pipeline_cache_hit(mock_entry: ConfigEntry) -> None:
    """Test Conversation entity using pre-generated turn from STT."""
    conv_entity = GeminiLiveConversationEntity(mock_entry)

    # Pre-populate turn_cache as if STT just ran
    mock_entry.runtime_data.turn_cache.store_turn(
        "Turn off the lights", "Lights turned off.", b"lights_off_audio"
    )

    user_input = ConversationInput(text="Turn off the lights", language="en")
    result = await conv_entity.async_process(user_input)

    assert result.response.speech["plain"]["speech"] == "Lights turned off."

    # Verify audio was moved to TTS cache
    cached_audio = mock_entry.runtime_data.turn_cache.pop_tts_audio(
        "Lights turned off."
    )
    assert cached_audio == b"lights_off_audio"


@pytest.mark.asyncio
async def test_conversation_entity_text_fallback(mock_entry: ConfigEntry) -> None:
    """Test Conversation entity handling direct typed text."""
    conv_entity = GeminiLiveConversationEntity(mock_entry)

    mock_entry.runtime_data.client.process_text_turn = AsyncMock(
        return_value=("Direct response text", b"direct_audio")
    )

    user_input = ConversationInput(text="Tell me a joke", language="en")
    result = await conv_entity.async_process(user_input)

    assert result.response.speech["plain"]["speech"] == "Direct response text"
    cached_audio = mock_entry.runtime_data.turn_cache.pop_tts_audio(
        "Direct response text"
    )
    assert cached_audio == b"direct_audio"


@pytest.mark.asyncio
async def test_tts_entity_cached_audio(mock_entry: ConfigEntry) -> None:
    """Test TTS entity returning pre-generated audio."""
    tts_entity = GeminiLiveTTSEntity(mock_entry)

    # Pre-populate TTS cache
    mock_entry.runtime_data.turn_cache.store_tts_audio("Hello there", b"\x00\x00" * 100)

    format_str, wav_bytes = await tts_entity.async_get_tts_audio("Hello there", "en")
    assert format_str == "wav"
    assert wav_bytes[:4] == b"RIFF"


@pytest.mark.asyncio
async def test_tts_entity_fallback(mock_entry: ConfigEntry) -> None:
    """Test TTS entity generating standalone audio when no cache exists."""
    tts_entity = GeminiLiveTTSEntity(mock_entry)

    mock_entry.runtime_data.client.generate_tts_audio = AsyncMock(
        return_value=b"RIFF_STANDALONE_WAV"
    )

    format_str, wav_bytes = await tts_entity.async_get_tts_audio("Custom alert", "en")
    assert format_str == "wav"
    assert wav_bytes == b"RIFF_STANDALONE_WAV"


@pytest.mark.asyncio
async def test_tts_supported_voices(mock_entry: ConfigEntry) -> None:
    """Test TTS supported voices."""
    tts_entity = GeminiLiveTTSEntity(mock_entry)
    voices = await tts_entity.async_get_supported_voices()
    assert voices is not None
    voice_names = [v.name for v in voices]
    assert "Puck" in voice_names
    assert "Charon" in voice_names
    assert "Kore" in voice_names
