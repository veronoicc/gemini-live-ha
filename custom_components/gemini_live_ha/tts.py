"""Text-to-Speech entity for Gemini Live HA."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.tts import (
    TextToSpeechEntity,
    TtsAudioType,
    Voice,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import GeminiLiveConfigEntry
from .client import pcm_to_wav
from .const import (
    CONF_MODEL,
    CONF_VOICE,
    DEFAULT_MODEL,
    DEFAULT_VOICE,
    DOMAIN,
    VOICES,
)
from .stt import SUPPORTED_LANGUAGES

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GeminiLiveConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Gemini Live TTS entity."""
    async_add_entities([GeminiLiveTTSEntity(entry)])


class GeminiLiveTTSEntity(TextToSpeechEntity):
    """Text-to-Speech entity producing natural Gemini spoken audio."""

    _attr_has_entity_name = True
    _attr_translation_key = "tts"
    _attr_should_poll = False

    def __init__(self, entry: GeminiLiveConfigEntry) -> None:
        """Initialize TTS entity."""
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_tts"

        model = entry.data.get(CONF_MODEL, DEFAULT_MODEL)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Gemini Live ({model})",
            manufacturer="Google",
            model=model,
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def supported_languages(self) -> list[str]:
        """Return list of supported languages."""
        return SUPPORTED_LANGUAGES

    @property
    def default_language(self) -> str:
        """Return default language."""
        return "en"

    @property
    def supported_options(self) -> list[str]:
        """Return list of supported options."""
        return [CONF_VOICE]

    @property
    def default_options(self) -> dict[str, Any]:
        """Return default options dictionary."""
        return {
            CONF_VOICE: self.entry.data.get(CONF_VOICE, DEFAULT_VOICE),
        }

    @callback
    def async_get_supported_voices(
        self, language: str | None = None
    ) -> list[Voice] | None:
        """Return list of supported voice presets."""
        return [Voice(voice_id=v, name=v) for v in VOICES]

    async def async_get_tts_audio(
        self,
        message: str,
        language: str,
        options: dict[str, Any] | None = None,
    ) -> TtsAudioType:
        """Get speech audio for given message."""
        turn_cache = self.entry.runtime_data.turn_cache
        client = self.entry.runtime_data.client

        # Step 1: Check if audio was pre-generated during STT/Conversation stages
        cached_pcm = turn_cache.pop_tts_audio(message)
        if cached_pcm is not None and len(cached_pcm) > 0:
            _LOGGER.debug(
                "TTS stage using cached audio for message: '%s' (%d bytes)",
                message,
                len(cached_pcm),
            )
            wav_bytes = pcm_to_wav(cached_pcm)
            return ("wav", wav_bytes)

        # Step 2: Fallback for standalone TTS requests (e.g. tts.speak service calls)
        _LOGGER.debug(
            "No cached audio found. Generating standalone TTS for: '%s'", message
        )
        try:
            wav_bytes = await client.generate_tts_audio(message)
            return ("wav", wav_bytes)
        except Exception:
            _LOGGER.exception("Error generating standalone TTS audio")
            raise
