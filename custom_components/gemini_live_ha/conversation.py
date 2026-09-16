"""Conversation entity for Gemini Live HA."""

from __future__ import annotations

import logging

from homeassistant.components.conversation import (
    ConversationEntity,
    ConversationEntityFeature,
    ConversationInput,
    ConversationResult,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import GeminiLiveConfigEntry
from .const import CONF_MODEL, DEFAULT_MODEL, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GeminiLiveConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Gemini Live conversation entity."""
    async_add_entities([GeminiLiveConversationEntity(entry)])


class GeminiLiveConversationEntity(ConversationEntity):
    """Conversation entity interfacing with Gemini Live API."""

    _attr_has_entity_name = True
    _attr_translation_key = "conversation"
    _attr_should_poll = False
    _attr_supported_features = ConversationEntityFeature.CONTROL

    def __init__(self, entry: GeminiLiveConfigEntry) -> None:
        """Initialize conversation entity."""
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_conversation"

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
        """Return supported languages."""
        return ["*"]

    async def async_process(self, user_input: ConversationInput) -> ConversationResult:
        """Process incoming conversation input."""
        client = self.entry.runtime_data.client
        turn_cache = self.entry.runtime_data.turn_cache

        # Step 1: Check if this turn was already processed by STT in this pipeline run
        cached = turn_cache.pop_turn(user_input.text)
        if cached is not None:
            model_text, audio_pcm = cached
            _LOGGER.debug(
                "Conversation stage retrieved pre-processed turn from STT: '%s'",
                model_text,
            )
            # Forward audio to TTS cache
            if audio_pcm:
                turn_cache.store_tts_audio(model_text, audio_pcm)

            response = intent.IntentResponse(language=user_input.language)
            response.async_set_speech(model_text)
            return ConversationResult(
                response=response,
                conversation_id=user_input.conversation_id,
            )

        # Step 2: Fallback for text-based Assist query (user typed text instead of voice)
        _LOGGER.debug(
            "No cached STT turn found. Processing text query: '%s'", user_input.text
        )
        try:
            model_text, audio_pcm = await client.process_text_turn(
                user_input.text, context=user_input.context
            )
            if not model_text:
                model_text = "I did not receive a response from Gemini."

            # Store generated audio in TTS cache in case TTS is invoked
            if audio_pcm:
                turn_cache.store_tts_audio(model_text, audio_pcm)

            response = intent.IntentResponse(language=user_input.language)
            response.async_set_speech(model_text)
            return ConversationResult(
                response=response,
                conversation_id=user_input.conversation_id,
            )
        except Exception as err:
            _LOGGER.exception("Error processing text query in Gemini Live conversation")
            response = intent.IntentResponse(language=user_input.language)
            response.async_set_error(
                intent.IntentResponseErrorCode.UNKNOWN,
                f"Error communicating with Gemini Live: {err}",
            )
            return ConversationResult(
                response=response,
                conversation_id=user_input.conversation_id,
            )
