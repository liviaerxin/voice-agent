import asyncio
import pyaudio
from app.realtime_transcribe_client import RealtimeTranscribeClient
import os
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)



OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Missing OpenAI API key.")


async def test_stream_audio_from_microphone(client: RealtimeTranscribeClient):
        """Start continuous audio streaming."""
        # Configure the audio format to as following requirements at [input_audio_format](https://platform.openai.com/docs/api-reference/realtime-sessions/create-transcription#realtime-sessions-create-transcription-input_audio_format):
        # - pcm16
        # - 24kHz sample rate
        # - single channel (mono), and little-endian byte order.

        print(f"test_stream_audio_from_microphone")
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

                await client.stream_audio(data)
                
            except Exception as e:
                print(f"Error streaming: {e}")
                break
            await asyncio.sleep(0.01)

async def main():
    client = RealtimeTranscribeClient(api_key=OPENAI_API_KEY)
    await client.connect()
    
    # 1. Run streaming and receiving concurrently.    
    # send_task =  asyncio.create_task(test_stream_audio_from_microphone(client))
    # receive_task = asyncio.create_task(client.receive_messages())
    # await asyncio.gather(send_task, receive_task)

    # 2. Async flow
    send_task =  asyncio.create_task(test_stream_audio_from_microphone(client))
    
    async for transcript in client.receive_messages():
        print("transcript:", transcript)
    
    await send_task
    
if __name__ == "__main__":
    asyncio.run(main())