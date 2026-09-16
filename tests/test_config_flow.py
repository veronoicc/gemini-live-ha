"""Tests for the config flow of Gemini Live HA."""

import pytest
from custom_components.gemini_live_ha.config_flow import (
    GeminiLiveConfigFlow,
    GeminiLiveOptionsFlowHandler,
)
from custom_components.gemini_live_ha.const import (
    CONF_API_KEY,
    CONF_EXPOSE_HA_CONTROL,
    CONF_GOOGLE_SEARCH,
    CONF_MODEL,
    CONF_TEMPERATURE,
    CONF_THINKING_LEVEL,
    CONF_VOICE,
    DEFAULT_MODEL,
    DEFAULT_VOICE,
    MODEL_3_8_LIVE_EXTENDED_THINKING,
    THINKING_LEVEL_MEDIUM,
    VOICE_CHARON,
)
from homeassistant.config_entries import ConfigEntry


@pytest.mark.asyncio
async def test_step_user_empty_api_key() -> None:
    """Test validation failure when API key is empty."""
    flow = GeminiLiveConfigFlow()
    result = await flow.async_step_user({CONF_API_KEY: "   "})

    assert result["type"] == "form"
    assert result["errors"] == {CONF_API_KEY: "invalid_api_key"}


@pytest.mark.asyncio
async def test_step_user_success_default() -> None:
    """Test successful configuration with default values."""
    flow = GeminiLiveConfigFlow()
    result = await flow.async_step_user(
        {
            CONF_API_KEY: "AIzaSyTestApiKey123",
            CONF_MODEL: DEFAULT_MODEL,
            CONF_VOICE: DEFAULT_VOICE,
        }
    )

    assert result["type"] == "create_entry"
    assert result["title"] == f"Gemini Live ({DEFAULT_MODEL})"
    assert result["data"][CONF_API_KEY] == "AIzaSyTestApiKey123"
    assert result["data"][CONF_MODEL] == DEFAULT_MODEL
    assert result["data"][CONF_VOICE] == DEFAULT_VOICE


@pytest.mark.asyncio
async def test_step_user_custom_model_and_voice() -> None:
    """Test successful configuration with custom model and thinking level."""
    flow = GeminiLiveConfigFlow()
    result = await flow.async_step_user(
        {
            CONF_API_KEY: "AIzaSyCustomKey",
            CONF_MODEL: MODEL_3_8_LIVE_EXTENDED_THINKING,
            CONF_VOICE: VOICE_CHARON,
            CONF_THINKING_LEVEL: THINKING_LEVEL_MEDIUM,
            CONF_TEMPERATURE: 0.7,
            CONF_GOOGLE_SEARCH: True,
            CONF_EXPOSE_HA_CONTROL: True,
        }
    )

    assert result["type"] == "create_entry"
    assert result["title"] == f"Gemini Live ({MODEL_3_8_LIVE_EXTENDED_THINKING})"
    assert result["data"][CONF_MODEL] == MODEL_3_8_LIVE_EXTENDED_THINKING
    assert result["data"][CONF_VOICE] == VOICE_CHARON
    assert result["data"][CONF_THINKING_LEVEL] == THINKING_LEVEL_MEDIUM
    assert result["data"][CONF_TEMPERATURE] == 0.7
    assert result["data"][CONF_GOOGLE_SEARCH] is True


@pytest.mark.asyncio
async def test_options_flow() -> None:
    """Test updating options."""
    entry = ConfigEntry(
        entry_id="test_entry",
        title="Gemini Live",
        data={CONF_API_KEY: "test_key", CONF_MODEL: DEFAULT_MODEL},
        options={},
    )
    handler = GeminiLiveOptionsFlowHandler(entry)

    # Initial view returns form
    form = await handler.async_step_init()
    assert form["type"] == "form"

    # Submitting updates creates entry
    result = await handler.async_step_init(
        {
            CONF_MODEL: MODEL_3_8_LIVE_EXTENDED_THINKING,
            CONF_VOICE: VOICE_CHARON,
            CONF_TEMPERATURE: 1.2,
        }
    )
    assert result["type"] == "create_entry"
    assert result["data"][CONF_MODEL] == MODEL_3_8_LIVE_EXTENDED_THINKING
    assert result["data"][CONF_VOICE] == VOICE_CHARON
    assert result["data"][CONF_TEMPERATURE] == 1.2
