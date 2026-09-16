"""Gemini Live HA integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .client import GeminiLiveClient
from .const import DOMAIN
from .turn_cache import TurnCache

__all__ = ["DOMAIN"]

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.STT,
    Platform.CONVERSATION,
    Platform.TTS,
]


@dataclass
class GeminiLiveRuntimeData:
    """Runtime data stored in the config entry."""

    client: GeminiLiveClient
    turn_cache: TurnCache
    options: dict[str, Any]


type GeminiLiveConfigEntry = ConfigEntry[GeminiLiveRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: GeminiLiveConfigEntry) -> bool:
    """Set up Gemini Live HA from a config entry."""
    config = {**entry.data, **entry.options}

    client = GeminiLiveClient(hass, config)
    turn_cache = TurnCache()

    entry.runtime_data = GeminiLiveRuntimeData(
        client=client,
        turn_cache=turn_cache,
        options=config,
    )

    # Listen for options updates to reload entry
    entry.async_on_unload(entry.add_update_listener(update_listener))

    # Forward setup to entity platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: GeminiLiveConfigEntry) -> bool:
    """Unload a Gemini Live HA config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        entry.runtime_data.turn_cache.clear()
    return unload_ok


async def update_listener(hass: HomeAssistant, entry: GeminiLiveConfigEntry) -> None:
    """Reload the config entry when options change."""
    _LOGGER.debug("Configuration updated, reloading Gemini Live entry %s", entry.title)
    await hass.config_entries.async_reload(entry.entry_id)
