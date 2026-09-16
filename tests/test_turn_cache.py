"""Tests for the TurnCache in Gemini Live HA."""

import time

from custom_components.gemini_live_ha.turn_cache import TurnCache, _normalize_text


def test_normalize_text() -> None:
    """Test text normalization."""
    assert _normalize_text("  Hello   World!  ") == "hello world!"
    assert _normalize_text("TURN ON LIGHTS") == "turn on lights"


def test_store_and_pop_turn_exact() -> None:
    """Test storing and popping an exact turn."""
    cache = TurnCache(ttl=60)
    cache.store_turn("Turn on the lamp", "Lamp is now on.", b"\x00\x01\x02")

    result = cache.pop_turn("Turn on the lamp")
    assert result is not None
    model_text, audio = result
    assert model_text == "Lamp is now on."
    assert audio == b"\x00\x01\x02"

    # Second pop should return None (already popped)
    assert cache.pop_turn("Turn on the lamp") is None


def test_pop_turn_normalized() -> None:
    """Test popping with case and whitespace variations."""
    cache = TurnCache(ttl=60)
    cache.store_turn("  Turn ON the light! ", "Done.", b"audio123")

    result = cache.pop_turn("turn on the light!")
    assert result is not None
    model_text, audio = result
    assert model_text == "Done."
    assert audio == b"audio123"


def test_store_and_pop_tts_audio() -> None:
    """Test TTS audio storage and retrieval."""
    cache = TurnCache(ttl=60)
    cache.store_tts_audio("Hello from Gemini", b"wav_raw_pcm")

    audio = cache.pop_tts_audio("hello from gemini")
    assert audio == b"wav_raw_pcm"
    assert cache.pop_tts_audio("hello from gemini") is None


def test_single_fresh_fallback() -> None:
    """Test popping the single fresh turn when text slightly differs."""
    cache = TurnCache(ttl=60)
    cache.store_turn("Turn on the bedroom light", "Bedroom light on", b"audio")

    # When query text is slightly different (e.g. STT post-processing in HA)
    result = cache.pop_turn("Turn on the bedroom lamp")
    assert result is not None
    model_text, _ = result
    assert model_text == "Bedroom light on"


def test_ttl_expiration() -> None:
    """Test that entries expire after TTL."""
    cache = TurnCache(ttl=0.01)
    cache.store_turn("Fast query", "Fast response", b"pcm")
    cache.store_tts_audio("Fast response", b"pcm")

    time.sleep(0.02)
    assert cache.pop_turn("Fast query") is None
    assert cache.pop_tts_audio("Fast response") is None


def test_clear() -> None:
    """Test clearing all cached entries."""
    cache = TurnCache(ttl=60)
    cache.store_turn("Query", "Response", b"pcm")
    cache.store_tts_audio("Response", b"pcm")

    cache.clear()
    assert cache.pop_turn("Query") is None
    assert cache.pop_tts_audio("Response") is None
