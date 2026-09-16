"""Pytest configuration and Home Assistant stubs for Gemini Live HA."""

from __future__ import annotations

import sys
from collections.abc import Callable
from enum import StrEnum
from typing import Any
from unittest.mock import MagicMock

# Stub Home Assistant modules if not installed
if "homeassistant" not in sys.modules:
    ha = MagicMock()

    class MockPlatform(StrEnum):
        STT = "stt"
        CONVERSATION = "conversation"
        TTS = "tts"

    ha.const.Platform = MockPlatform
    ha.const.MATCH_ALL = "*"

    def mock_callback(func: Any) -> Any:
        return func

    ha.core.callback = mock_callback

    class MockConfigEntry:
        def __init__(
            self,
            entry_id: str = "test_entry_id",
            title: str = "Test Entry",
            data: dict | None = None,
            options: dict | None = None,
        ) -> None:
            self.entry_id = entry_id
            self.title = title
            self.data = data or {}
            self.options = options or {}
            self.runtime_data = None
            self._update_listeners: list[Callable] = []

        def add_update_listener(self, listener: Callable) -> Callable:
            self._update_listeners.append(listener)
            return listener

        def async_on_unload(self, callback: Callable) -> None:
            pass

    ha.config_entries.ConfigEntry = MockConfigEntry

    class MockConfigFlow:
        def __init_subclass__(cls, domain: str = "", **kwargs: Any) -> None:
            super().__init_subclass__(**kwargs)
            cls._domain = domain

        def __init__(self) -> None:
            self._unique_id: str | None = None

        async def async_set_unique_id(self, unique_id: str) -> None:
            self._unique_id = unique_id

        def _abort_if_unique_id_configured(self) -> None:
            pass

        def async_create_entry(self, title: str, data: dict) -> dict:
            return {"type": "create_entry", "title": title, "data": data}

        def async_show_form(
            self, step_id: str, data_schema: Any, errors: dict | None = None
        ) -> dict:
            return {
                "type": "form",
                "step_id": step_id,
                "data_schema": data_schema,
                "errors": errors or {},
            }

    ha.config_entries.ConfigFlow = MockConfigFlow

    class MockOptionsFlow:
        _config_entry: MockConfigEntry | None = None

        @property
        def config_entry(self) -> MockConfigEntry:
            if self._config_entry is None:
                raise AttributeError("config_entry not set")
            return self._config_entry

        def async_create_entry(self, title: str, data: dict) -> dict:
            return {"type": "create_entry", "title": title, "data": data}

        def async_show_form(
            self, step_id: str, data_schema: Any, errors: dict | None = None
        ) -> dict:
            return {
                "type": "form",
                "step_id": step_id,
                "data_schema": data_schema,
                "errors": errors or {},
            }

    ha.config_entries.OptionsFlow = MockOptionsFlow

    # STT stubs
    ha.components.stt.AudioFormats.WAV = "wav"
    ha.components.stt.AudioCodecs.PCM = "pcm"
    ha.components.stt.AudioBitRates.BITRATE_16 = 16
    ha.components.stt.AudioSampleRates.SAMPLERATE_16000 = 16000
    ha.components.stt.AudioChannels.CHANNEL_MONO = 1

    class MockSpeechResultState(StrEnum):
        SUCCESS = "success"
        ERROR = "error"

    ha.components.stt.SpeechResultState = MockSpeechResultState

    class MockSpeechResult:
        def __init__(self, text: str | None, result: MockSpeechResultState) -> None:
            self.text = text
            self.result = result

    ha.components.stt.SpeechResult = MockSpeechResult

    class MockSpeechAudioProcessing:
        def __init__(self, **kwargs: Any) -> None:
            pass

    ha.components.stt.SpeechAudioProcessing = MockSpeechAudioProcessing

    class MockSpeechToTextEntity:
        _attr_has_entity_name = True
        _attr_translation_key = ""
        _attr_should_poll = False
        _context = None

    ha.components.stt.SpeechToTextEntity = MockSpeechToTextEntity

    # Conversation stubs
    class MockConversationEntityFeature:
        CONTROL = 1

    ha.components.conversation.ConversationEntityFeature = MockConversationEntityFeature

    class MockConversationResult:
        def __init__(self, response: Any, conversation_id: str | None = None) -> None:
            self.response = response
            self.conversation_id = conversation_id

    ha.components.conversation.ConversationResult = MockConversationResult

    class MockConversationInput:
        def __init__(
            self,
            text: str,
            context: Any = None,
            conversation_id: str | None = None,
            language: str = "en",
        ) -> None:
            self.text = text
            self.context = context
            self.conversation_id = conversation_id
            self.language = language

    ha.components.conversation.ConversationInput = MockConversationInput

    class MockIntentSpeech:
        def __init__(self, speech: str) -> None:
            self.speech = {"plain": {"speech": speech}}

    class MockIntentResponse:
        def __init__(self, language: str = "en") -> None:
            self.language = language
            self.speech: dict[str, Any] = {}

        def async_set_speech(self, text: str) -> None:
            self.speech = {"plain": {"speech": text}}

        def async_set_error(self, code: str, message: str) -> None:
            self.speech = {"plain": {"speech": message}}

    ha.helpers.intent.IntentResponse = MockIntentResponse

    class MockConversationEntity:
        _attr_has_entity_name = True
        _attr_translation_key = ""
        _attr_should_poll = False
        _attr_supported_features = 0

    ha.components.conversation.ConversationEntity = MockConversationEntity

    # TTS stubs
    class MockVoice:
        def __init__(self, voice_id: str, name: str) -> None:
            self.voice_id = voice_id
            self.name = name

    ha.components.tts.Voice = MockVoice

    class MockTextToSpeechEntity:
        _attr_has_entity_name = True
        _attr_translation_key = ""
        _attr_should_poll = False

    ha.components.tts.TextToSpeechEntity = MockTextToSpeechEntity

    # Device info
    class MockDeviceEntryType(StrEnum):
        SERVICE = "service"

    ha.helpers.device_registry.DeviceEntryType = MockDeviceEntryType

    class MockDeviceInfo:
        def __init__(self, **kwargs: Any) -> None:
            for k, v in kwargs.items():
                setattr(self, k, v)

    ha.helpers.device_registry.DeviceInfo = MockDeviceInfo
    ha.util.ssl.get_default_context = MagicMock(return_value=MagicMock())

    # Register in sys.modules
    sys.modules["homeassistant"] = ha
    sys.modules["homeassistant.config_entries"] = ha.config_entries
    sys.modules["homeassistant.const"] = ha.const
    sys.modules["homeassistant.core"] = ha.core
    sys.modules["homeassistant.components"] = ha.components
    sys.modules["homeassistant.components.stt"] = ha.components.stt
    sys.modules["homeassistant.components.conversation"] = ha.components.conversation
    sys.modules["homeassistant.components.tts"] = ha.components.tts
    sys.modules["homeassistant.helpers"] = ha.helpers
    sys.modules["homeassistant.helpers.device_registry"] = ha.helpers.device_registry
    sys.modules["homeassistant.helpers.entity_platform"] = ha.helpers.entity_platform
    sys.modules["homeassistant.helpers.intent"] = ha.helpers.intent
    sys.modules["homeassistant.helpers.selector"] = ha.helpers.selector
    sys.modules["homeassistant.util"] = ha.util
    sys.modules["homeassistant.util.ssl"] = ha.util.ssl
