# Gemini Live HA

Home Assistant integration providing ultra-low latency, bidirectional real-time voice and audio streaming using the **Gemini Live API**.

## Features

- **Real-Time Bidirectional Voice**: Connects directly to Google's Gemini Live WebSocket endpoint (`BidiGenerateContent`) for natural, low-latency spoken conversations.
- **Multiple API Key Instances**: Set up multiple integration instances, each with its own Google AI Studio API key, model, and voice preferences.
- **Full Model Selection**:
  - `gemini-3.8-live` (Default)
  - `gemini-3.8-live-extended-thinking`
  - `gemini-3.1-flash-live-preview`
  - `gemini-2.5-flash-native-audio-preview-12-2025`
- **Voice Customization**: Select from Google's natural prebuilt voices (`Puck`, `Charon`, `Kore`, `Fenrir`, `Aoede`).
- **Assist Pipeline Integration**: Exposes **STT** (Speech-to-Text), **Conversation**, and **TTS** (Text-to-Speech) entities per instance.
- **Integrated Smart Home Control**: Gemini can directly execute commands and query entity states in Home Assistant via function calling.
- **Configurable Options**: Fine-tune system instructions, temperature, thinking level, Google Search grounding, and smart home control via UI Options Flow.
- **Multilingual Support**: UI translations in English, German, Spanish, French, Italian, Dutch, and Polish.

## Assist Pipeline Setup

Because the Gemini Live API operates as a unified, real-time bidirectional stream, optimal operation in Home Assistant requires selecting all three entities in a single Assist Pipeline:

1. In Home Assistant, go to **Settings** -> **Voice Assistants** -> **Assist**.
2. Click **Add Pipeline** (or edit an existing one).
3. Set:
   - **Speech-to-text**: `Gemini Live (Speech to Text)`
   - **Conversation agent**: `Gemini Live (Conversation)`
   - **Text-to-speech**: `Gemini Live (Text to Speech)`
4. Save the pipeline and set it as default or use it with your voice satellites and browser microphone.

> **Note**: If you type text into the Assist dialog or call `tts.speak` standalone, the Conversation and TTS entities also provide full independent fallbacks.

## Installation via HACS

1. Add this repository as a Custom Repository in HACS (Integration).
2. Download and restart Home Assistant.
3. In Home Assistant, navigate to **Settings** -> **Devices & Services** -> **Add Integration** -> **Gemini Live HA**.
4. Enter your Google AI Studio API key and configure your options.
