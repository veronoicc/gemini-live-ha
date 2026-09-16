"""Config flow for the Gemini Live HA integration."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_API_KEY,
    CONF_EXPOSE_HA_CONTROL,
    CONF_GOOGLE_SEARCH,
    CONF_MODEL,
    CONF_SYSTEM_INSTRUCTION,
    CONF_TEMPERATURE,
    CONF_THINKING_LEVEL,
    CONF_VOICE,
    DEFAULT_EXPOSE_HA_CONTROL,
    DEFAULT_GOOGLE_SEARCH,
    DEFAULT_MODEL,
    DEFAULT_SYSTEM_INSTRUCTION,
    DEFAULT_TEMPERATURE,
    DEFAULT_THINKING_LEVEL,
    DEFAULT_VOICE,
    DOMAIN,
    MODELS,
    THINKING_LEVELS,
    VOICES,
)

_LOGGER = logging.getLogger(__name__)


def _model_options() -> list[SelectOptionDict]:
    return [SelectOptionDict(value=m, label=m) for m in MODELS]


def _voice_options() -> list[SelectOptionDict]:
    return [SelectOptionDict(value=v, label=v) for v in VOICES]


def _thinking_level_options() -> list[SelectOptionDict]:
    return [SelectOptionDict(value=t, label=t) for t in THINKING_LEVELS]


class GeminiLiveConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Gemini Live HA."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            if not api_key:
                errors[CONF_API_KEY] = "invalid_api_key"
            else:
                # Key hash for unique entry per API key
                key_hash = hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:12]
                await self.async_set_unique_id(f"gemini_live_{key_hash}")
                self._abort_if_unique_id_configured()

                model = user_input.get(CONF_MODEL, DEFAULT_MODEL)
                title = f"Gemini Live ({model})"

                return self.async_create_entry(
                    title=title,
                    data={
                        CONF_API_KEY: api_key,
                        CONF_MODEL: model,
                        CONF_VOICE: user_input.get(CONF_VOICE, DEFAULT_VOICE),
                        CONF_SYSTEM_INSTRUCTION: user_input.get(
                            CONF_SYSTEM_INSTRUCTION, DEFAULT_SYSTEM_INSTRUCTION
                        ),
                        CONF_TEMPERATURE: user_input.get(
                            CONF_TEMPERATURE, DEFAULT_TEMPERATURE
                        ),
                        CONF_THINKING_LEVEL: user_input.get(
                            CONF_THINKING_LEVEL, DEFAULT_THINKING_LEVEL
                        ),
                        CONF_GOOGLE_SEARCH: user_input.get(
                            CONF_GOOGLE_SEARCH, DEFAULT_GOOGLE_SEARCH
                        ),
                        CONF_EXPOSE_HA_CONTROL: user_input.get(
                            CONF_EXPOSE_HA_CONTROL, DEFAULT_EXPOSE_HA_CONTROL
                        ),
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_API_KEY): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)
                ),
                vol.Required(CONF_MODEL, default=DEFAULT_MODEL): SelectSelector(
                    SelectSelectorConfig(
                        options=_model_options(),
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(CONF_VOICE, default=DEFAULT_VOICE): SelectSelector(
                    SelectSelectorConfig(
                        options=_voice_options(),
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_SYSTEM_INSTRUCTION, default=DEFAULT_SYSTEM_INSTRUCTION
                ): TextSelector(TextSelectorConfig(multiline=True)),
                vol.Optional(
                    CONF_TEMPERATURE, default=DEFAULT_TEMPERATURE
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=0.0,
                        max=2.0,
                        step=0.1,
                        mode=NumberSelectorMode.SLIDER,
                    )
                ),
                vol.Optional(
                    CONF_THINKING_LEVEL, default=DEFAULT_THINKING_LEVEL
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=_thinking_level_options(),
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_GOOGLE_SEARCH, default=DEFAULT_GOOGLE_SEARCH
                ): BooleanSelector(),
                vol.Optional(
                    CONF_EXPOSE_HA_CONTROL, default=DEFAULT_EXPOSE_HA_CONTROL
                ): BooleanSelector(),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return GeminiLiveOptionsFlowHandler(config_entry)


class GeminiLiveOptionsFlowHandler(OptionsFlow):
    """Handle options flow for Gemini Live HA."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        entry_data = {**self.config_entry.data, **self.config_entry.options}

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_MODEL, default=entry_data.get(CONF_MODEL, DEFAULT_MODEL)
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=_model_options(),
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(
                    CONF_VOICE, default=entry_data.get(CONF_VOICE, DEFAULT_VOICE)
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=_voice_options(),
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_SYSTEM_INSTRUCTION,
                    default=entry_data.get(
                        CONF_SYSTEM_INSTRUCTION, DEFAULT_SYSTEM_INSTRUCTION
                    ),
                ): TextSelector(TextSelectorConfig(multiline=True)),
                vol.Optional(
                    CONF_TEMPERATURE,
                    default=entry_data.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=0.0,
                        max=2.0,
                        step=0.1,
                        mode=NumberSelectorMode.SLIDER,
                    )
                ),
                vol.Optional(
                    CONF_THINKING_LEVEL,
                    default=entry_data.get(CONF_THINKING_LEVEL, DEFAULT_THINKING_LEVEL),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=_thinking_level_options(),
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_GOOGLE_SEARCH,
                    default=entry_data.get(CONF_GOOGLE_SEARCH, DEFAULT_GOOGLE_SEARCH),
                ): BooleanSelector(),
                vol.Optional(
                    CONF_EXPOSE_HA_CONTROL,
                    default=entry_data.get(
                        CONF_EXPOSE_HA_CONTROL, DEFAULT_EXPOSE_HA_CONTROL
                    ),
                ): BooleanSelector(),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
