
# Voice Agent Server Prototype

## Introduction

This Prototype project implements a **Voice Agent** using the **OpenAI** ecosystem, built around **Speech-to-Text**, **LLM**, and **Text-to-Speech**.

There are two main architectures for implementing a voice agent:

### 1. Speech-to-Speech

- **Low latency**, **Near real-time**
- Less control and predictability
- APIs used:
  - Realtime API

### 2. Speech-to-Text → LLM → Text-to-Speech (current approach)

- **added latency**
- More control and flexibility
- APIs used:
  - [Realtime API/Transcription](https://platform.openai.com/docs/guides/realtime-transcription)
  - Chat Completions API
  - Speech API

### API Streaming Capabilities

| API             | Input            | Output           | Streaming Support |
|----------------|------------------|------------------|-------------------|
| Realtime API   | Audio (stream)   | Audio (stream)   | ✅ Full duplex     |
| Transcription  | Audio (full)     | Text (stream)    | ✅                 |
| Chat Completion| Text (full)      | Text (stream)    | ✅                 |
| Speech         | Text (full)      | Audio (stream)   | ✅                 |

> **Note:** The Realtime API offers true full-duplex streaming, enabling lowest latency. Our current implementation uses the STT → LLM → TTS flow, which introduces latency due to sequential processing.

### Latency Optimizations

To reduce latency in the current pipeline:

1. **Realtime API/Transcription** - transcribe the ongoing audio input, as `browser microphone streams audio -> our server streams audio -> OpenAI Realtime Transcription -> text`.
2. **In-memory audio buffer** – avoids file I/O delays
3. **Streaming audio playback** – streams audio from OpenAI to the browser as it's generated
4. **PCM format** – raw, low-latency audio format reduces encoding/decoding overhead and get fast response from OpenAI API

Here we **Realtime API/Transcription** to replace **Transcription API** to reduce latency. See [Latency Analysis](#latency-analysis) for details.

## Tech Stack

| Component    | Tool / API                             | Reason                                           |
|--------------|----------------------------------------|--------------------------------------------------|
| Audio Format | PCM (streaming in/out)                 | Raw format ensures low-latency transmission      |
| Transport    | WebSocket                              | Enables async, bi-directional streaming          |
| STT          | `gpt-4o-mini-transcribe` (OpenAI)      | Accurate, streaming-capable speech-to-text       |
| LLM          | `gpt-4.1-mini` (OpenAI ChatCompletion) | Low-latency, concise responses                   |
| TTS          | `gpt-4o-mini-tts` (OpenAI)             | Fast, natural-sounding speech with stream output |
| Backend      | Python + FastAPI + WebSocket           | Async-native server suitable for real-time apps  |
| Client       | HTML5 + JS + Web Audio API             | Lightweight browser-based voice interaction      |

### WebSocket vs WebRTC

- **Client ↔ OpenAI**: WebRTC (for native client integration)
- **Client ↔ Server ↔ OpenAI**: WebSocket (for server-side control and architecture flexibility)

We use **WebSocket** for browser compatibility and easier server orchestration.

### Audio Format Considerations

| Format     | Pros                                             | Cons                         |
|------------|--------------------------------------------------|------------------------------|
| PCM        | Fastest response, no decoding needed             | Larger raw size              |
| WAV        | Similar to PCM but includes headers              | Slightly larger               |
| webm/Opus  | Smaller size                                     | Slower to decode, adds delay |

- Preferred:
  - **PCM**: 24kHz, 16-bit, mono, little-endian, for realtime api
  - **WAV**: Input file for STT
- Refer to [OpenAI Supported Formats](https://platform.openai.com/docs/guides/text-to-speech#supported-output-formats)

### Streaming vs Real-time

**Streaming ≠ Real-time**

| Capability       | Description                                                                 |
|------------------|-----------------------------------------------------------------------------|
| Real-time STT    | Audio streamed in → text streamed out as it's recognized                   |
| Real-time TTS    | Text streamed in → audio streamed out as it's synthesized                  |
| Chat LLM         | Text streamed out as response is generated (token by token)                |

> For true real-time, the system must handle **stream-in and stream-out** simultaneously across STT, LLM, and TTS.

## System Architecture

```text
Client (Mic Input)
     ↓ WebSocket
Audio Stream
     ↓
Server
     ↓
Audio Stream
     ↓
[Real-time API/Transcription] GPT-4o mini Transcribe
     ↓
[Chat Completions API] GPT-4.1 mini (1-word response)
     ↓
[Speech API] GPT-4o mini tts
     ↓ WebSocket
Audio Stream
     ↓
Streaming audio playback on browser
```

## Getting Started

### Requirements

- Python 3.10+

### Install dependencies

```sh
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Setup `.env`

Place your `.env` file with `OPENAI_API_KEY` at the project root.

### Run Development Server

```sh
uvicorn main:app --reload
```

### Run Production Server

```sh
python main.py
```

### Access Client

Open your browser at [http://127.0.0.1:8000/client](http://127.0.0.1:8000/client)

### Example: Test Real-time Transcription

> Uses OpenAI Realtime API directly.

```sh
python -m examples.test_realtime_transcribe_client
```

## Demo

![Watch the video](https://github.com/user-attachments/assets/4c7e55ba-f48f-43ab-839c-0dbca66aeda2)

## Implementation Checklist

- [x] Audio WebSocket Server
  - [x] Buffer audio input
  - [x] Serve static client (HTML + JS) for demo
- [x] Speech-to-Text (Realtime API/STT)
  - [x] Transcribe complete audio input
  - [x] Transcribe ongoing audio input, with voice activity detection (VAD)
- [x] LLM Response (GPT-4.1 mini)
- [x] Text-to-Speech (TTS)
  - [x] Send full audio response
  - [x] Stream partial audio for long responses
- [x] Browser Client
  - [x] Record mic audio and send via WebSocket (PCM16, 24kHz, mono)
  - [x] Play back PCM audio in real-time
  - [x] Use voice activity detection (VAD) to replace manual recording
- [] Concurrent load testing
- [] Decouple STT / LLM / TTS into microservices

## Latency Analysis

### Example 1: Short speech

```sh
2025-05-21 15:40:19.353 - INFO - HTTP Request: POST https://api.openai.com/v1/audio/speech "HTTP/1.1 200 OK"
2025-05-21 15:40:19.450 - INFO - 
[Speech detected]
2025-05-21 15:40:19.936 - INFO - 
[Speech ended]
2025-05-21 15:40:20.767 - INFO - 
[Transcription completed]
transcribed_text: How are you?
2025-05-21 15:40:20.767 - INFO - LLM start...
2025-05-21 15:40:21.265 - INFO - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2025-05-21 15:40:21.323 - INFO - llm_response_text: Fine.
2025-05-21 15:40:21.323 - INFO - TTS start...
2025-05-21 15:40:21.906 - INFO - HTTP Request: POST https://api.openai.com/v1/audio/speech "HTTP/1.1 200 OK"
```

Audio ended → STT: ~0.8s
LLM Response: ~0.5s
TTS Start to First Output: ~0.6s

### Example 2: Longer speech

```sh
2025-05-21 15:50:38.447 - INFO - 
[Speech detected]
2025-05-21 15:50:47.164 - INFO - 
[Speech ended]
2025-05-21 15:50:49.435 - INFO - 
[Transcription completed]
transcribed_text: Could you tell me about your feeling if the weather is bad or if it's a cloudy day, how will you feel? Will you feel good or will you feel bad?
2025-05-21 15:50:49.435 - INFO - LLM start...
2025-05-21 15:50:49.953 - INFO - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2025-05-21 15:50:49.968 - INFO - llm_response_text: Neutral
2025-05-21 15:50:49.968 - INFO - TTS start...
2025-05-21 15:50:50.527 - INFO - HTTP Request: POST https://api.openai.com/v1/audio/speech "HTTP/1.1 200 OK"
```


Audio ended → STT: ~2.3s, shorter than using Transcription API as it takes ~4s.
LLM Response: ~0.6s
TTS Start to First Output: ~0.6s


So, The **STT** process is the primary latency bottleneck, especially for longer speech inputs.

## Further Improvements

### Reduce Latency

- Host closer to OpenAI (e.g., in Azure)
- Deploy **on-prem** STT/TTS models (e.g., Whisper, Coqui)
- Use **true realtime** services by leverage streaming on the whole data pipeline:
  - Streaming STT input → Streaming LLM → Streaming TTS

### Scalability

- Split system into microservices for STT, LLM, and TTS

### Security

- Use **SSL** for secure audio input/output transport

### Functionality

- Refactor the project
- Add test cases
- Handle HTTP error
  - 400 for missing/invalid input.oReturn
  - HTTP 502 with meaningful errors for STT, LLM, or TTS failures
- Handle edge cases and failures in WebSocket messages
- Use **state machine** for fine-grained control over STT/LLM/TTS pipeline

## Bonus

We can build a **fully local desktop voice agent** using OpenAI's Realtime API with full streaming support.

## Conclusion

This project demonstrates how to prototype a real-time voice assistant using OpenAI's APIs with low-latency audio streaming, simplified architecture, and scalable components.

## References

- [OpenAI Audio API Docs](https://platform.openai.com/docs/guides/audio)
- [Streaming Speech-to-Text](https://platform.openai.com/docs/guides/audio/speech-to-text)
- [Text-to-Speech Formats](https://platform.openai.com/docs/guides/text-to-speech#supported-output-formats)
- [Voice Activity Detection (VAD)](https://platform.openai.com/docs/guides/realtime-vad)
- [GitHub - alesaccoia/VoiceStreamAI: Near-Realtime audio transcription using self-hosted Whisper and WebSocket in Python/JS](https://github.com/alesaccoia/VoiceStreamAI)
- [From Gemini API to Local: Building a Fully Open-Source Realtime Multimodal Assistant](https://yeyu.substack.com/p/from-gemini-api-to-local-building)
- [GitHub - tomcatmwi/browser-pcm16mono: Demo files for my article titled 'Streaming audio with 16–bit mono PCM encoding from the browser (and how to mix audio, while we are at it)'](https://github.com/tomcatmwi/browser-pcm16mono)
- [Realtime API (Advanced Voice Mode) Python Implementation - #12 by NuclearGeek - API - OpenAI Developer Community](https://community.openai.com/t/realtime-api-advanced-voice-mode-python-implementation/964636/12)