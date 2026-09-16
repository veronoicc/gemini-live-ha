"""Speech-to-Text entity for Gemini Live HA."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterable

from homeassistant.components.stt import (
    AudioBitRates,
    AudioChannels,
    AudioCodecs,
    AudioFormats,
    AudioSampleRates,
    SpeechAudioProcessing,
    SpeechMetadata,
    SpeechResult,
    SpeechResultState,
    SpeechToTextEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import GeminiLiveConfigEntry
from .const import CONF_MODEL, DEFAULT_MODEL, DOMAIN

_LOGGER = logging.getLogger(__name__)

# Broad list of languages supported by Gemini audio models
SUPPORTED_LANGUAGES: list[str] = [
    "en",
    "en-US",
    "de",
    "es",
    "fr",
    "it",
    "nl",
    "pl",
    "pt",
    "ja",
    "ko",
    "zh",
    "ru",
    "hi",
    "ar",
    "tr",
    "sv",
    "da",
    "no",
    "fi",
    "el",
    "cs",
    "uk",
    "ro",
    "hu",
    "th",
    "vi",
    "id",
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GeminiLiveConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Gemini Live STT entity."""
    async_add_entities([GeminiLiveSTTEntity(entry)])


class GeminiLiveSTTEntity(SpeechToTextEntity):
    """Speech-to-text entity streaming directly to Gemini Live API."""

    _attr_has_entity_name = True
    _attr_translation_key = "stt"
    _attr_should_poll = False

    def __init__(self, entry: GeminiLiveConfigEntry) -> None:
        """Initialize STT entity."""
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_stt"

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
    def supported_formats(self) -> list[AudioFormats]:
        """Return list of supported audio formats."""
        return [AudioFormats.WAV]

    @property
    def supported_codecs(self) -> list[AudioCodecs]:
        """Return list of supported audio codecs."""
        return [AudioCodecs.PCM]

    @property
    def supported_bit_rates(self) -> list[AudioBitRates]:
        """Return list of supported bit rates."""
        return [AudioBitRates.BITRATE_16]

    @property
    def supported_sample_rates(self) -> list[AudioSampleRates]:
        """Return list of supported sample rates."""
        return [AudioSampleRates.SAMPLERATE_16000]

    @property
    def supported_channels(self) -> list[AudioChannels]:
        """Return list of supported channels."""
        return [AudioChannels.CHANNEL_MONO]

    @property
    def audio_processing(self) -> SpeechAudioProcessing:
        """Return required audio processing settings."""
        return SpeechAudioProcessing(
            requires_external_vad=True,
            prefers_auto_gain_enabled=False,
            prefers_noise_reduction_enabled=False,
        )

    async def async_process_audio_stream(
        self, metadata: SpeechMetadata, stream: AsyncIterable[bytes]
    ) -> SpeechResult:
        """Process incoming audio stream using Gemini Live WebSocket."""
        client = self.entry.runtime_data.client
        turn_cache = self.entry.runtime_data.turn_cache

        try:
            user_text, model_text, audio_pcm = await client.process_audio_turn(
                stream, context=self._context
            )

            if not user_text and not model_text:
                _LOGGER.warning("Gemini Live STT received empty speech and response")
                return SpeechResult(text=None, result=SpeechResultState.ERROR)

            # If user_text was empty but model responded, use a fallback user_text
            effective_user_text = user_text or "voice command"

            # Cache the turn so Conversation entity can retrieve it instantly
            turn_cache.store_turn(effective_user_text, model_text, audio_pcm)

            return SpeechResult(
                text=effective_user_text,
                result=SpeechResultState.SUCCESS,
            )
        except Exception:
            _LOGGER.exception("Error processing audio stream in Gemini Live STT")
            return SpeechResult(text=None, result=SpeechResultState.ERROR)
