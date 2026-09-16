"""Tests for integration setup and lifecycle."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from custom_components.gemini_live_ha import async_setup_entry, async_unload_entry
from homeassistant.config_entries import ConfigEntry


@pytest.mark.asyncio
async def test_setup_and_unload_entry() -> None:
    """Test setting up and unloading the integration."""
    hass = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

    entry = ConfigEntry(
        entry_id="test_entry_id",
        title="Gemini Live",
        data={"api_key": "test_api_key", "model": "gemini-3.8-live"},
        options={},
    )

    # Setup
    result = await async_setup_entry(hass, entry)
    assert result is True
    assert entry.runtime_data is not None
    assert entry.runtime_data.client is not None
    assert entry.runtime_data.turn_cache is not None
    hass.config_entries.async_forward_entry_setups.assert_called_once()

    # Unload
    unload_result = await async_unload_entry(hass, entry)
    assert unload_result is True
    hass.config_entries.async_unload_platforms.assert_called_once()
