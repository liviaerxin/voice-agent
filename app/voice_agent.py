from openai import AsyncOpenAI
from fastapi import WebSocket
from typing import Union, IO
import logging
import aiofiles
import io
import logging

logger = logging.getLogger(__name__)


class VoiceAgentOpenAI:
    """Voice Agent using OpenAI APIs
    | Chunk Size     | Latency | Network Overhead | Use Case                     |
    | -------------- | ------- | ---------------- | ---------------------------- |
    | 200 bytes      | \~4 ms  | High             | Ultra-low-latency (gaming)   |
    | 500-1500 bytes | \~21 ms | Low/Moderate     | ✅ Good balance (voice agent) |
    | 4000 bytes     | \~85 ms | Low              | Buffered playback (music)    |

    """

    def __init__(
        self,
        stt_model: str = "gpt-4o-mini-transcribe",
        tts_model: str = "gpt-4o-mini-tts",
        llm_model: str = "gpt-4.1-mini",
        voice: str = "coral",
        chunk_size: int = 500,
    ):
        self.stt_model = stt_model
        self.tts_model = tts_model
        self.llm_model = llm_model
        self.voice = voice
        self.audio_format = "wav"
        self.audio_codec = "pcm"
        self.chunk_size = chunk_size
        self.client = AsyncOpenAI()

    async def speech_to_text_transcribe_async(self, audio: Union[str, IO]) -> str:
        is_filepath = isinstance(audio, str)

        if is_filepath:
            # It's a filepath, so we open the file
            logger.debug(f"Open audio filepath [{audio}]")
            f = await aiofiles.open(audio, "rb")
            audio_file = await f.read()
        else:
            logger.debug(f"Use audio fileobj size: [{len(audio)}]")
            audio_file = io.BytesIO(audio)
            audio_file.name = f"audio.{self.audio_format}"  # <-- Important! Must set a fake filename

        transcript = ""

        stream = await self.client.audio.transcriptions.create(
            model=self.stt_model,
            file=audio_file,
            response_format="text",
            prompt="Realtime transcribe",
            language="en",
            stream=True,
        )

        async for event in stream:
            if event.type == "transcript.text.delta":
                logger.debug(event.delta, end="", flush=True)
                transcript += event.delta

        if is_filepath:
            audio_file.close()

        return transcript

    async def text_to_speech_async(self, text: str, output_path: str = "output.pcm"):
        async with self.client.audio.speech.with_streaming_response.create(
            model=self.tts_model,
            voice=self.voice,
            input=text,
            instructions="Speak in a cheerful and positive tone. language English",
            response_format=self.audio_codec,
        ) as response:
            # await LocalAudioPlayer().play(response)
            await response.stream_to_file(output_path)
            logger.info(f"Saved audio to {output_path}")

    async def text_to_speech_streaming_websocket(self, text: str, ws: WebSocket, output_path: str = None):
        async with self.client.audio.speech.with_streaming_response.create(
            model=self.tts_model,
            voice=self.voice,
            input=text,
            instructions="Speak in a cheerful and positive tone. language English",
            response_format=self.audio_codec,
        ) as response:
            # Save into file
            audio_file = None
            if output_path:
                audio_file = await aiofiles.open(output_path, "wb")

            async for data in response.iter_bytes(self.chunk_size):
                # Stream to ws
                logger.info(f"Streaming speech to client, data size[{len(data)}]")
                await ws.send_bytes(data)
                if audio_file:
                    # Stream to file
                    await audio_file.write(data)

            if audio_file:
                await audio_file.close()

    async def call_llm_async(self, user_input: str) -> str:
        answer = ""
        prompt = "You’re a helpful assistant. You reply with only one word."
        stream = await self.client.chat.completions.create(
            model=self.llm_model,
            messages=[{"role": "system", "content": prompt}, {"role": "user", "content": user_input}],
            stream=True,
        )

        async for chunk in stream:
            content = chunk.choices[0].delta.content
            if content is not None:
                answer += content
                logger.debug(content, end="", flush=True)

        return answer
