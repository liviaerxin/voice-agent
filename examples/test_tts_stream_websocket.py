import asyncio
import websockets
from openai import AsyncOpenAI

async def stream_tts_to_websocket(websocket):
    client = AsyncOpenAI()
    async with client.audio.speech.with_streaming_response.create(
        model="gpt-4o-mini-tts",
        voice="nova",
        input="This is a real-time streamed response.",
        response_format="wav",  # Use WAV for easier playback in browser
        language="en"
    ) as response:
        async for chunk in response.iter_bytes():
            await websocket.send(chunk)

async def main():
    async with websockets.serve(stream_tts_to_websocket, "localhost", 8765):
        print("WebSocket server started on ws://localhost:8765")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())