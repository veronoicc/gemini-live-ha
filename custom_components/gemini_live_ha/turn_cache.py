"""Turn cache for correlating Assist pipeline stages in Gemini Live HA."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

_LOGGER = logging.getLogger(__name__)

DEFAULT_TTL_SECONDS = 120.0


@dataclass(slots=True)
class CachedTurn:
    """Represents a cached conversation turn from STT to Conversation."""

    user_text: str
    model_text: str
    audio_pcm: bytes
    timestamp: float = field(default_factory=time.monotonic)


@dataclass(slots=True)
class CachedAudio:
    """Represents cached audio from Conversation to TTS."""

    audio_pcm: bytes
    timestamp: float = field(default_factory=time.monotonic)


def _normalize_text(text: str) -> str:
    """Normalize text for reliable matching across pipeline stages."""
    return " ".join(text.strip().lower().split())


class TurnCache:
    """Thread-safe cache correlating STT, Conversation, and TTS stages."""

    def __init__(self, ttl: float = DEFAULT_TTL_SECONDS) -> None:
        """Initialize turn cache."""
        self._ttl = ttl
        self._turns: dict[str, CachedTurn] = {}
        self._tts_audios: dict[str, CachedAudio] = {}

    def _purge_expired(self) -> None:
        """Evict stale cache entries."""
        now = time.monotonic()
        expired_turns = [
            k for k, v in self._turns.items() if now - v.timestamp > self._ttl
        ]
        for k in expired_turns:
            self._turns.pop(k, None)

        expired_tts = [
            k for k, v in self._tts_audios.items() if now - v.timestamp > self._ttl
        ]
        for k in expired_tts:
            self._tts_audios.pop(k, None)

    def store_turn(self, user_text: str, model_text: str, audio_pcm: bytes) -> None:
        """Store a completed live turn from STT."""
        self._purge_expired()
        key = _normalize_text(user_text)
        if not key:
            key = "__empty__"
        self._turns[key] = CachedTurn(
            user_text=user_text,
            model_text=model_text,
            audio_pcm=audio_pcm,
        )
        _LOGGER.debug("Stored turn in cache for key: '%s'", key)

    def pop_turn(self, user_text: str) -> tuple[str, bytes] | None:
        """Retrieve and remove a stored turn for the conversation stage."""
        self._purge_expired()
        key = _normalize_text(user_text)
        turn = self._turns.pop(key, None)
        if turn is not None:
            _LOGGER.debug("Found matching turn in cache for key: '%s'", key)
            return turn.model_text, turn.audio_pcm

        # Fallback: if only one turn exists in cache and it's fresh (< 10s), pop it
        if len(self._turns) == 1:
            only_key, only_turn = next(iter(self._turns.items()))
            if time.monotonic() - only_turn.timestamp < 10.0:
                self._turns.pop(only_key)
                _LOGGER.debug("Popped single fresh turn fallback for key: '%s'", key)
                return only_turn.model_text, only_turn.audio_pcm

        _LOGGER.debug("No cached turn found for key: '%s'", key)
        return None

    def store_tts_audio(self, model_text: str, audio_pcm: bytes) -> None:
        """Store pre-generated audio for the TTS stage."""
        self._purge_expired()
        key = _normalize_text(model_text)
        if not key:
            key = "__empty__"
        self._tts_audios[key] = CachedAudio(audio_pcm=audio_pcm)
        _LOGGER.debug("Stored TTS audio in cache for key: '%s'", key)

    def pop_tts_audio(self, model_text: str) -> bytes | None:
        """Retrieve and remove pre-generated audio for TTS."""
        self._purge_expired()
        key = _normalize_text(model_text)
        cached = self._tts_audios.pop(key, None)
        if cached is not None:
            _LOGGER.debug("Found matching TTS audio in cache for key: '%s'", key)
            return cached.audio_pcm

        # Fallback: if only one audio item exists in cache and it's fresh (< 10s), pop it
        if len(self._tts_audios) == 1:
            only_key, only_cached = next(iter(self._tts_audios.items()))
            if time.monotonic() - only_cached.timestamp < 10.0:
                self._tts_audios.pop(only_key)
                _LOGGER.debug(
                    "Popped single fresh TTS audio fallback for key: '%s'", key
                )
                return only_cached.audio_pcm

        _LOGGER.debug("No cached TTS audio found for key: '%s'", key)
        return None

    def clear(self) -> None:
        """Clear all cached entries."""
        self._turns.clear()
        self._tts_audios.clear()
