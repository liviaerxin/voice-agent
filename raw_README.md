# Voice Agent Server


## Introduction

We use **OpenAI** ecosystem to develop a **Voice Agent** via **Speech-to-text / LLM / Text-to-speech** way.

There are two ways to implement the voice agent:

1. Speech-to-speech
    - low latency, true realtime
    - less control and predictability
    - API used
      - Realtime API
      - Chat Completions API
2. Speech-to-text / LLM / Text-to-speech
    - added latency, nearly realtime
    - more control and predictability
    - API used
      - Transcription API
      - Speech API
      - Chat Completions API

About those API streaming feature:
- Chat Completions API: text full in and text streaming out
- Transcription API: audio full in and text streaming out
- Speech API: text full in and audio streaming out
- Realtime API: audio streaming in and audio streaming out

Regarding the features from these API, **Realtime API** support streaming in and out, so it can have low latency, while other API would add latency.
So, here the **Speech-to-text / LLM / Text-to-speech** method we used can not reach the true **Realtime**, compared to **Speech-to-speech** which can reduce latency by leverage **Streaming in out out** features by **Realtime API**.

To achieve low latency in **Speech-to-text / LLM / Text-to-speech** method as much as possible, we have done:

1. in-memory buffer for audio, avoid file open/close
2. audio streaming response: Streaming realtime audio streamed from openai to the client, so the client can play the audio as the openai generate ongoing audio before full generated. It's good for long audio.
3. use `PCM` for best response and low latency in network and reduce decoding time.

However, it still take almost 4s to complete one round ask/answer. More details on [](#latency-analysis).

## Tech Stacks

| Component       | Tool / API                                             | Reason                                                               |
|-----------------|--------------------------------------------------------|----------------------------------------------------------------------|
| Audio Format    | `WAV` for file input, `PCM` for input/output streaming | Enables low-latency real-time streaming fast response                |
| Audio Transport | WebSocket                                              | Enables low-latency real-time streaming server-to-server application |
| STT             | gpt-4o-mini-transcribe(OpenAI)                         | Accurate, easy-to-use, supports streaming (see OpenAI STT API)       |
| LLM             | gpt-4.1-mini(OpenAI ChatCompletion)                    | Low-latency, efficient for 1-word response, compliant with task      |
| TTS             | gpt-4o-mini-tts(OpenAI)                                | Natural voice, fast streaming output (ElevenLabs supports stream)    |
| Backend         | Python + FastAPI + WebSocket                           | Async-first design, great for handling real-time streams             |
| Client          | HTML5 + JS WebSocket + AudioContext                    | Minimal setup, easy browser-based mic and audio playback             |

### About **WebSocket** vs **WebRTC**

client-side environments: Client <----> OpenAI realtime API, via WebRTC
server-to-server applications: Client <----> Server <----> OpenAI realtime API, via WebSocket

So we choose `Websocket`.

### About Audio Format/Codec

Our priority is **minimal delay from audio generation to playback**, then:

- Audio size is secondary (you’re dealing with small, short audio bursts).
- Latency is king — especially:
  - Encoding latency (how fast audio is prepared)
  - Transmission latency (network + WebSocket chunk delivery)
  - Decoding/playback latency (how fast the browser or app starts playing)
  - Fast response times from TTS of OpenAI

As these following format:
- [] webm/Opus: slow response times, small size, need decoding.
- [x] PCM: fastest response times, suitable for low-latency, without header, media size, raw data without decoding, streaming friendly and easy to implement in the prototype to show.
  - 4kHz (16-bit signed, low-endian)
- [x] WAV: Similar to PCM

Transcription API: **WAV** for input audio.
Speech API: **PCM** for output audio (24kHz, 16-bit signed, low-endian)
Realtime API(transcription): **PCM** for input audio (24kHz, 16-bit signed, mono, low-endian)

[supported-output-formats](https://platform.openai.com/docs/guides/text-to-speech#supported-output-formats)

### About Streaming and Realtime

**Streaming** != **Realtime**

For True Realtime in TTS:
Means: Audio is generated and sent back as the text is spoken, often token-by-token or phoneme-by-phoneme.
1. Starts generating audio before the full text is available.
2. Delivers audio in small chunks as they’re synthesized.
3. Often uses WebSocket or HTTP chunked transfer to send audio while it's still being generated.
Summary: text streaming in and audio streaming out

For True Realtime in STT:
Summary: audio streaming in and text streaming out

[choosing-the-right-api](https://platform.openai.com/docs/guides/audio#choosing-the-right-api)

## System Architecture

```sh
Client (Browser Mic) ───> WebSocket ──┬──> Audio Input Buffer
                                     │
                                     └─> [STT] OpenAI GPT-4o Transcribe
                                               ↓
                                     ┌─> [LLM] GPT-4.1 mini (1-word response)
                                     ↓
                          [TTS] GPT-4o mini
                                     ↓ WebSocket
                     Streaming audio playback on browser
```

TTS:

- openai generate the full audio file, client download full audio file then play.
- openai generate the full audio file, client download part audio file while playing.
- openai generate the part audio file, client download part audio file while playing.

## Getting Started

Running `Python3.10+`,

Install deps,

```sh
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

Move your `.env` containing `OPENAI_API_KEY` to the top folder.
 
In dev,

```sh
uvicorn main:app --reload
```

In production,

```sh
python main.py
```

Then visit [minimal client](http://127.0.0.1:8000/client)


Run `test_realtime_transcribe_client` example, it will show realtime transcription in your console.
> NOTE: It directly communicate with OpenAI realtime API

```sh
python -m examples.test_realtime_transcribe_client
```

## Implementation Checklist

- [x] Audio API server
  - [x] Receive audio in buffer
  - [x] Serve a minimal HTML+JavaScript client statically
- [x] Speech-to-Text (STT)
  - [x] Streaming the transcription of a completed audio recording
  - [] Streaming the transcription of an ongoing audio recording
- [x] LLM Response (GPT-4.1 mini)
- [x] Text-to-Speech (TTS)
  - [x] Send back whole the speech to client.
  - [x] Streaming the ongoing speech to client, especially when the text is large, it will take long time to generate whole speech.
- [x] A minimal HTML+JavaScript client(browser/Chrome)
  - [x] Captures microphone input and sends raw audio(PCM16 24kHZ mono) via WebSocket.
    - [x] Start/Stop button to start recording and stop recording.
    - [] Future: add Voice activity detection to detect voice stop, remove manual start/stop recording. 
  - [x] Receives raw audio(PCM16 24kHZ mono) from the server and plays it in real-time.
- [] Support multiple users access, Not test!
- [] Concurrent pressure test
- [] Decouple the STT/LLM/TTS from the server as micro services
- [] [Voice activity detection (VAD)](https://platform.openai.com/docs/guides/realtime-vad)

## Latency Analysis

Here we can see the main latency in the voice agent is contributed by the `Speech to Text`:

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

STT for generating `Hello, how are you?`, takes ~1.7s = [12:52:53.763 - 12:52:52.027]
LLM for answering `Fine`, takes ~0.8s
TTS for getting the first response data, takes ~0.6s, getting the last data takes ~1s.

If we test a longer speech,

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

STT takes ~4s = [12:57:31.631 - 12:57:27.643]
LLM takes ~0.8s
TTS takes ~0.6s

As we see, SST consumes more time as the speech time grow.

## Further Improvements

Latency:
- Get our voice agent server close to the STT/LLM/TTS cloud service provider, such as deploying in Azure to use those service provided by Azure.
- Deploy a **local/on-premise** SST/TTS model, like Huggingface's **Voice Activity Detection** (VAD) and OpenAI's **Whisper** model.
- Use **Realtime SST/LLM/TTS** services that support both streaming in and out features:
  - Transcribe the ongoing audio stream to text stream.
  - LLM answering the ongoing text stream to test stream
  - Syntheise the ongoing text stream to audio stream.

Scalable:
- Divide into services in microserive

Security:
- Transport the input and output audio in SSL


Functionallity:
- Auto detect the audio bound, avoid manual turn detection (like push-to-talk) by using Start/Stop button.
- Raise missing/invalid audio input and meaningful errors for STT, LLM, or TTS failures in websocket to notify the client.
- Use state machine to fine control the Input/SST/LLM/TTS/Output workflow.

## Bonus

We can develop the voice agent as local desktop by fully using realtime api from openai

## Conclusion

## References

[OpenAI real-time API: speech-to-speech and transcription.](https://platform.openai.com/docs/guides/realtime)

[A demo combining the Realtime API with Twilio to build an AI calling assistant](https://github.com/openai/openai-realtime-twilio-demo)

[A demonstration of handoffs between Realtime API voice agents with reasoning model validation.](https://github.com/openai/openai-realtime-agents)


https://github.com/alesaccoia/VoiceStreamAI

https://yeyu.substack.com/p/from-gemini-api-to-local-building