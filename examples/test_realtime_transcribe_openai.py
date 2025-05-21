import asyncio
import websockets
import json
import base64
import pyaudio
import aiofiles
from pathlib import Path
import os

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Missing OpenAI API key.")

# Replace with your actual OpenAI API key
API_KEY = OPENAI_API_KEY
URI = "wss://api.openai.com/v1/realtime"

AUDIO_FILE = Path(__file__).parent / "lathe_G711.org_.wav"

final_transcription = ""
transcript_buffer = ""


async def transcribe():
    print("transcribe")

    headers = {"Authorization": f"Bearer {API_KEY}", "OpenAI-Beta": "realtime=v1"}
    url = f"{URI}?intent=transcription"  # &model=gpt-4o-realtime-preview-2024-10-01

    async with websockets.connect(url, additional_headers=headers) as ws:
        # 1. Setup the transcription session
        await setup_transcribe_session(ws)

        # Create an event to signal if speech stopped is detected.
        speech_stopped_event = asyncio.Event()

        # 2. Create task for stream audio to the open websocket
        send_task = asyncio.create_task(stream_audio(ws))
        # send_task = asyncio.create_task(
        #     stream_audio_from_file(ws, file_path=AUDIO_FILE, chunk_size=1024, speech_stopped_event=speech_stopped_event)
        # )

        # 3. Create task for receive event from the open websocket
        receive_task = asyncio.create_task(receive_messages(ws, speech_stopped_event))

        # 4. Run streaming and receiving concurrently.
        await asyncio.gather(send_task, receive_task)


async def setup_transcribe_session(ws):
    print("Setup the transcription session")
    session_config = {
        "type": "transcription_session.update",
        "session": {
            "input_audio_format": "pcm16",
            "input_audio_transcription": {
                # "model": "gpt-4o-mini-transcribe",
                "model": "whisper-1",
                "prompt": "realtime transcribe",
                "language": "en",
            },
            "turn_detection": {
                "type": "server_vad",
                "threshold": 0.5,
                "prefix_padding_ms": 300,
                "silence_duration_ms": 500,
            },
            "input_audio_noise_reduction": {"type": "near_field"},
            "include": [
                "item.input_audio_transcription.logprobs",
            ],
        },
    }

    await ws.send(json.dumps(session_config))


async def stream_audio(ws):
    """Start continuous audio streaming."""
    # Configure the audio format to as following requirements at [input_audio_format](https://platform.openai.com/docs/api-reference/realtime-sessions/create-transcription#realtime-sessions-create-transcription-input_audio_format):
    # - pcm16
    # - 24kHz sample rate
    # - single channel (mono), and little-endian byte order.

    print(f"stream_audio")
    RATE = 24000
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1

    stream = pyaudio.PyAudio().open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)

    print("\nStreaming audio... Press 'q' to stop.")

    while True:
        try:
            # Read raw PCM data
            data = stream.read(CHUNK, exception_on_overflow=False)
            # Stream directly without trying to decode

            """Stream raw audio data to the API."""
            audio_b64 = base64.b64encode(data).decode()

            append_event = {"type": "input_audio_buffer.append", "audio": audio_b64}
            await ws.send(json.dumps(append_event))

        except Exception as e:
            print(f"Error streaming: {e}")
            break
        await asyncio.sleep(0.01)


async def stream_audio_from_file(ws, file_path: str, chunk_size: int, speech_stopped_event: asyncio.Event):
    """
    Read the local ulaw file and send it in chunks.
    After finishing, wait for 1 second to see if the server auto-commits.
    If not, send a commit event manually.
    """
    try:
        async with aiofiles.open(file_path, "rb") as f:
            while True:
                chunk = await f.read(chunk_size)
                if not chunk:
                    break
                # Base64-encode the audio chunk.
                audio_chunk = base64.b64encode(chunk).decode("utf-8")
                audio_event = {"type": "input_audio_buffer.append", "audio": audio_chunk}
                await ws.send(json.dumps(audio_event))
                await asyncio.sleep(0.02)  # simulate real-time streaming
        print("Finished sending audio file.")

        # Wait 1 second to allow any late VAD events before committing.
        try:
            await asyncio.wait_for(speech_stopped_event.wait(), timeout=1.0)
            print("Speech stopped event received; no manual commit needed.")
        except asyncio.TimeoutError:
            commit_event = {"type": "input_audio_buffer.commit"}
            await ws.send(json.dumps(commit_event))
            print("Manually sent input_audio_buffer.commit event.")
    except FileNotFoundError:
        print(f"Audio file not found: {file_path}")
    except Exception as e:
        print("Error sending audio: %s", e)

async def receive_messages(ws, speech_stopped_event: asyncio.Event):
    global final_transcription
    try:
        async for message in ws:
            try:
                data = json.loads(message)
                event_type = data.get("type")

                if event_type == "error":
                    print(f"Error: {data['error']}")
                    continue

                # Handle interruptions
                elif event_type == "input_audio_buffer.speech_started":
                    print("\n[Speech detected")

                elif event_type == "input_audio_buffer.speech_stopped":
                    print("\n[Speech ended]")

                # Handle normal response events
                elif event_type == "response.text.delta":
                    delta = data["delta"]
                    # print(f"\n[response.text.delta] [{delta}]")

                elif event_type == "response.audio.delta":
                    audio_bytes = base64.b64decode(data["delta"])
                    # print(f"\n[response.audio.delta] [{audio_bytes}]")

                # Handle input audio transcription
                elif event_type == "conversation.item.input_audio_transcription.completed":
                    transcript = data.get("transcript", "")
                    print(f"Transcription {transcript}")

                elif event_type == "conversation.item.input_audio_transcription.delta":
                    delta = data.get("delta", "")
                    print("Transcription delta: %s", delta)
                    final_transcription += delta

                # Handle output audio transcription
                elif event_type == "response.audio_transcript.delta":
                    delta = data.get("delta", "")
                    transcript_buffer += delta
                    print("Response Transcription delta: %s", delta)

                elif event_type == "response.audio_transcript.done":
                    print("response.audio_transcript.done")

                else:
                    pass

            except Exception as ex:
                print("Error processing message: %s", ex)
    except Exception as e:
        print("Error receiving events: %s", e)


if __name__ == "__main__":
    asyncio.run(transcribe())
