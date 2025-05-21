"""
```sh
python -m tests.test_tts
```
"""

from pathlib import Path
from openai import OpenAI
from openai import AsyncOpenAI
from openai.helpers import LocalAudioPlayer
import asyncio

speech_file_path = Path(__file__).parent / "speech.wav"

model="gpt-4o-mini-tts"
voice="coral"


def text_to_audio(text: str, output_path="output.wav"):
    client = OpenAI()
    with client.audio.speech.with_streaming_response.create(
        model=model,
        voice=voice,
        input=text,
        instructions="Speak in a cheerful and positive tone.",
        response_format=Path(output_path).suffix.lstrip('.')
    ) as response:
        # LocalAudioPlayer().play(response)
        response.stream_to_file(speech_file_path)
        print(f"Saved audio to {output_path}")

async def text_to_audio_async(text: str, output_path="output.wav"):
    client = AsyncOpenAI()
    async with client.audio.speech.with_streaming_response.create(
        model=model,
        voice=voice,
        input=text,
        instructions="Speak in a cheerful and positive tone.",
        response_format=Path(output_path).suffix.lstrip('.'),
    ) as response:
        # await LocalAudioPlayer().play(response)
        await response.stream_to_file(speech_file_path)
        print(f"Saved audio to {output_path}")
        
if __name__ == "__main__":
    # synthesize(text="Today is a wonderful day to build something people love!", output_path=speech_file_path.as_posix())
    asyncio.run(text_to_audio_async(text="Today is a wonderful day to build something people love!", output_path=speech_file_path.as_posix()))