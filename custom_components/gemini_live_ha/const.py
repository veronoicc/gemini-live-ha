"""Constants for the Gemini Live HA integration."""

from typing import Final

DOMAIN: Final = "gemini_live_ha"

# Configuration keys
CONF_API_KEY: Final = "api_key"
CONF_MODEL: Final = "model"
CONF_VOICE: Final = "voice"
CONF_SYSTEM_INSTRUCTION: Final = "system_instruction"
CONF_TEMPERATURE: Final = "temperature"
CONF_THINKING_LEVEL: Final = "thinking_level"
CONF_GOOGLE_SEARCH: Final = "google_search"
CONF_EXPOSE_HA_CONTROL: Final = "expose_ha_control"

# Supported models requested by user
MODEL_2_5_FLASH_NATIVE_AUDIO: Final = "gemini-2.5-flash-native-audio-preview-12-2025"
MODEL_3_1_FLASH_LIVE_PREVIEW: Final = "gemini-3.1-flash-live-preview"
MODEL_3_8_LIVE: Final = "gemini-3.8-live"
MODEL_3_8_LIVE_EXTENDED_THINKING: Final = "gemini-3.8-live-extended-thinking"

MODELS: Final[list[str]] = [
    MODEL_3_8_LIVE,
    MODEL_3_8_LIVE_EXTENDED_THINKING,
    MODEL_3_1_FLASH_LIVE_PREVIEW,
    MODEL_2_5_FLASH_NATIVE_AUDIO,
]

# Supported voices
VOICE_PUCK: Final = "Puck"
VOICE_CHARON: Final = "Charon"
VOICE_KORE: Final = "Kore"
VOICE_FENRIR: Final = "Fenrir"
VOICE_AOEDE: Final = "Aoede"

VOICES: Final[list[str]] = [
    VOICE_PUCK,
    VOICE_CHARON,
    VOICE_KORE,
    VOICE_FENRIR,
    VOICE_AOEDE,
]

# Thinking levels (applicable to models supporting thinking)
THINKING_LEVEL_OFF: Final = "off"
THINKING_LEVEL_LOW: Final = "low"
THINKING_LEVEL_MEDIUM: Final = "medium"
THINKING_LEVEL_HIGH: Final = "high"

THINKING_LEVELS: Final[list[str]] = [
    THINKING_LEVEL_OFF,
    THINKING_LEVEL_LOW,
    THINKING_LEVEL_MEDIUM,
    THINKING_LEVEL_HIGH,
]

# Defaults
DEFAULT_MODEL: Final = MODEL_3_8_LIVE
DEFAULT_VOICE: Final = VOICE_PUCK
DEFAULT_TEMPERATURE: Final = 1.0
DEFAULT_THINKING_LEVEL: Final = THINKING_LEVEL_OFF
DEFAULT_GOOGLE_SEARCH: Final = False
DEFAULT_EXPOSE_HA_CONTROL: Final = True

DEFAULT_SYSTEM_INSTRUCTION: Final = (
    "You are a helpful smart home voice assistant running in Home Assistant. "
    "Provide clear, concise, conversational answers suitable for spoken audio playback. "
    "When the user asks to control smart home devices or query status, execute the command "
    "using your tools and respond with a concise confirmation."
)

# Audio specifications
INPUT_SAMPLE_RATE: Final = 16000
OUTPUT_SAMPLE_RATE: Final = 24000
SAMPLE_WIDTH: Final = 2  # 16-bit PCM (2 bytes)
CHANNELS: Final = 1  # Mono

# Gemini Live WebSocket URL
GEMINI_LIVE_WS_ENDPOINT: Final = (
    "wss://generativelanguage.googleapis.com/ws/"
    "google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent"
)
