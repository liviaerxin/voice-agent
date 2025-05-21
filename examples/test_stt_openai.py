"""
[OpenAI: Speech to text](https://platform.openai.com/docs/guides/speech-to-text)

```sh
python -m tests.test_stt
```

"""

from pathlib import Path
from openai import OpenAI
from openai import AsyncOpenAI
import asyncio


speech_file_path = Path(__file__).parent / "speech.wav"

model="gpt-4o-mini-transcribe"


def audio_to_text_transcribe(audio_path: str):
    client = OpenAI()
    audio_file = open(audio_path, "rb")
    transcription = client.audio.transcriptions.create(
        model=model, 
        file=audio_file
    )

    return transcription.text

async def audio_to_text_transcribe_async(audio_path: str):
    client = AsyncOpenAI()
    
    audio_file = await asyncio.to_thread(open, audio_path, "rb")
    transcript = ""
    
    stream = await client.audio.transcriptions.create(
        model=model,
        file=audio_file,
        response_format="text",
        stream=True,
    )
  
    async for event in stream:
        if event.type == "transcript.text.delta":
            print(event.delta, end="", flush=True)
            transcript += event.delta
            
    audio_file.close()
    return transcript

if __name__ == "__main__":
    # print("Transcription:", audio_to_text_transcribe(speech_file_path.as_posix()))
    
    result = asyncio.run(audio_to_text_transcribe_async(speech_file_path.as_posix()))
    print(result)