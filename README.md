
# Voice Agent Server

## Introduction

This project implements a **Voice Agent** using the **OpenAI** ecosystem, built around **Speech-to-Text**, **LLM**, and **Text-to-Speech**.

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
  - Transcription API
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

1. **In-memory audio buffer** – avoids file I/O delays
2. **Streaming audio playback** – streams audio from OpenAI to the browser as it's generated
3. **PCM format** – raw, low-latency audio format reduces encoding/decoding overhead

Still, the response will increase as the speech getting longer . See [Latency Analysis](#latency-analysis) for details.

## Tech Stack

| Component    | Tool / API                                      | Reason                                                         |
|--------------|--------------------------------------------------|----------------------------------------------------------------|
| Audio Format | WAV (file input), PCM (streaming in/out)         | Raw format ensures low-latency transmission                    |
| Transport    | WebSocket                                         | Enables async, bi-directional streaming                        |
| STT          | `gpt-4o-mini-transcribe` (OpenAI)                | Accurate, streaming-capable speech-to-text                    |
| LLM          | `gpt-4.1-mini` (OpenAI ChatCompletion)           | Low-latency, concise responses                                 |
| TTS          | `gpt-4o-mini-tts` (OpenAI)                       | Fast, natural-sounding speech with stream output               |
| Backend      | Python + FastAPI + WebSocket                     | Async-native server suitable for real-time apps               |
| Client       | HTML5 + JS + Web Audio API                       | Lightweight browser-based voice interaction                   |

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
  - **PCM**: 24kHz, 16-bit, mono, little-endian
  - **WAV**: Input for STT
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
Audio Input Buffer
     ↓
[STT] GPT-4o Transcribe
     ↓
[LLM] GPT-4.1 mini (1-word response)
     ↓
[TTS] GPT-4o mini
     ↓ WebSocket
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

[Download or view the video](./screen_record/screen_20250521.mp4)

## Implementation Checklist

- [x] Audio WebSocket Server
  - [x] Buffer audio input
  - [x] Serve static client (HTML + JS) for demo
- [x] Speech-to-Text (STT)
  - [x] Transcribe complete audio input
  - [] Transcribe ongoing audio input
- [x] LLM Response (GPT-4.1 mini)
- [x] Text-to-Speech (TTS)
  - [x] Send full audio response
  - [x] Stream partial audio for long responses
- [x] Browser Client
  - [x] Record mic audio and send via WebSocket (PCM16, 24kHz, mono)
  - [x] Play back PCM audio in real-time
  - [] Use voice activity detection (VAD) to replace manual recording
- [] Concurrent load testing
- [] Decouple STT / LLM / TTS into microservices
- [] [Voice Activity Detection (OpenAI Docs)](https://platform.openai.com/docs/guides/realtime-vad)

## Latency Analysis

### Example 1: Short speech

```sh
INFO:     connection open
2025-05-21 12:52:49.767 - INFO - Setup the transcription session
2025-05-21 12:52:49.768 - INFO - Session[16acea63-9bf2-4d92-84ed-c67f3261f73a] start
2025-05-21 12:52:49.768 - INFO - Session[16acea63-9bf2-4d92-84ed-c67f3261f73a] Seq[0] start
2025-05-21 12:52:52.027 - INFO - Save audio buffer size[95532] and audio file to [data/16acea63-9bf2-4d92-84ed-c67f3261f73a/0_in_16_24kHZ_mono.wav]
2025-05-21 12:52:52.027 - INFO - SST start...
2025-05-21 12:52:53.763 - INFO - HTTP Request: POST https://api.openai.com/v1/audio/transcriptions "HTTP/1.1 200 OK"
2025-05-21 12:52:53.840 - INFO - transcribed_text: How are you?
2025-05-21 12:52:53.840 - INFO - LLM start...
2025-05-21 12:52:54.686 - INFO - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2025-05-21 12:52:54.689 - INFO - llm_response_text: Great!
2025-05-21 12:52:54.689 - INFO - TTS start...
2025-05-21 12:52:55.708 - INFO - HTTP Request: POST https://api.openai.com/v1/audio/speech "HTTP/1.1 200 OK"
2025-05-21 12:52:55.709 - INFO - Streaming speech to client, data size[500]
2025-05-21 12:52:55.709 - INFO - Streaming speech to client, data size[500]
...
2025-05-21 12:52:55.822 - INFO - Streaming speech to client, data size[500]
2025-05-21 12:52:55.823 - INFO - Streaming speech to client, data size[200]
2025-05-21 12:52:55.825 - INFO - speech save to: data/16acea63-9bf2-4d92-84ed-c67f3261f73a/0_out.pcm
2025-05-21 12:52:55.825 - INFO - Session[16acea63-9bf2-4d92-84ed-c67f3261f73a] Seq[0] close
2025-05-21 12:52:55.825 - INFO - Session[16acea63-9bf2-4d92-84ed-c67f3261f73a] Seq[1] start
```

Audio Received → STT: ~1.7s
LLM Response: ~0.8s
TTS Start to First Output: ~0.6s
Total round-trip: ~3.5–4s

### Example 2: Longer speech

```sh
2025-05-21 12:57:27.643 - INFO - SST start...
2025-05-21 12:57:31.631 - INFO - HTTP Request: POST https://api.openai.com/v1/audio/transcriptions "HTTP/1.1 200 OK"
2025-05-21 12:57:31.915 - INFO - transcribed_text: Could you tell me about your feeling if the weather is bad or if it's a cloudy day? How will you feel? Will you feel good or will you feel bad?
2025-05-21 12:57:31.915 - INFO - LLM start...
2025-05-21 12:57:32.664 - INFO - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2025-05-21 12:57:32.708 - INFO - llm_response_text: Neutral
2025-05-21 12:57:32.708 - INFO - TTS start...
2025-05-21 12:57:33.317 - INFO - HTTP Request: POST https://api.openai.com/v1/audio/speech "HTTP/1.1 200 OK"
2025-05-21 12:57:33.318 - INFO - Streaming speech to client, data size[500]
...
2025-05-21 12:57:33.399 - INFO - Streaming speech to client, data size[300]
2025-05-21 12:57:33.401 - INFO - speech save to: data/16acea63-9bf2-4d92-84ed-c67f3261f73a/1_out.pcm
2025-05-21 12:57:33.401 - INFO - Session[16acea63-9bf2-4d92-84ed-c67f3261f73a] Seq[1] close
2025-05-21 12:57:33.401 - INFO - Session[16acea63-9bf2-4d92-84ed-c67f3261f73a] Seq[2] start
```


Audio Received → STT: ~4s
LLM Response: ~0.8s
TTS Start to First Output: ~0.6s


So, The **STT** process is the primary latency bottleneck, especially for longer speech inputs.

## Further Improvements

### Reduce Latency

- Host closer to OpenAI (e.g., in Azure)
- Deploy **on-prem** STT/TTS models (e.g., Whisper, Coqui)
- Use **true realtime** services:
  - Streaming STT input → Streaming LLM → Streaming TTS

### Scalability

- Split system into microservices for STT, LLM, and TTS

### Security

- Use **SSL** for secure audio input/output transport

### Functionality

- Auto-detect speech start/end using VAD
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
