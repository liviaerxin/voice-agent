
import websockets
import json
import base64
from pathlib import Path
import websockets
from fastapi import WebSocket
import os
import logging

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Missing OpenAI API key.")

# Replace with your actual OpenAI API key
API_KEY = OPENAI_API_KEY
OPENAI_REALTIME_URI = "wss://api.openai.com/v1/realtime"


class RealtimeTranscribeClient:
    def __init__(self, api_key: str, transcribe_model: str = "gpt-4o-mini-transcribe"):
        self.api_key = api_key
        self.base_uri = "wss://api.openai.com/v1/realtime"
        self.transcribe_model = transcribe_model
        self.openai_ws = None
        self.input_audio_format = "pcm16"

    async def connect(self):
        logger.info("Connected to OpenAI Realtime API!")
        headers = {"Authorization": f"Bearer {self.api_key}", "OpenAI-Beta": "realtime=v1"}
        url = f"{self.base_uri}?intent=transcription"  # &model=gpt-4o-realtime-preview-2024-10-01

        self.openai_ws = await websockets.connect(url, additional_headers=headers)

        # Set up default transcription session configure
        await self.setup_transcribe_session()

    async def setup_transcribe_session(self):
        logger.info("Setup the transcription session")

        session_config = {
            "type": "transcription_session.update",
            "session": {
                "input_audio_format": self.input_audio_format,
                "input_audio_transcription": {
                    # "model": "gpt-4o-mini-transcribe",
                    "model": self.transcribe_model,
                    "prompt": "Transcribe the incoming audio in real time. language English",
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

        await self.openai_ws.send(json.dumps(session_config))

    async def stream_audio(self, audio_chunk: bytes) -> None:
        """Stream raw audio data to the API."""
        audio_b64 = base64.b64encode(audio_chunk).decode()

        append_event = {"type": "input_audio_buffer.append", "audio": audio_b64}
        await self.openai_ws.send(json.dumps(append_event))

    async def receive_messages(self):
        try:
            async for message in self.openai_ws:
                try:
                    data = json.loads(message)
                    event_type = data.get("type")

                    if event_type == "error":
                        logger.info(f"Error: {data['error']}")
                        continue

                    # Handle interruptions
                    elif event_type == "input_audio_buffer.speech_started":
                        logger.info("\n[Speech detected]")

                    elif event_type == "input_audio_buffer.speech_stopped":
                        logger.info("\n[Speech ended]")

                    # Handle input audio transcription
                    elif event_type == "conversation.item.input_audio_transcription.completed":
                        logger.info(f"\n[Transcription completed]")
                        transcript = data.get("transcript", "")

                        yield transcript  # Yield the transcript here

                    elif event_type == "conversation.item.input_audio_transcription.delta":
                        logger.debug(f"\n[Transcription delta]")
                        # delta = data.get("delta", "")
                        # logger.info("Transcription delta: %s", delta)
                        # final_transcription += delta
                        pass

                    else:
                        pass

                except Exception as ex:
                    logger.info("Error processing message: %s", ex)
        except Exception as e:
            logger.info("Error receiving events: %s", e)
