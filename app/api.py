from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uuid
import asyncio
import json
import wave
import io
import aiofiles
import os
import logging
from openai import AsyncOpenAI
from pathlib import Path
from app.realtime_transcribe_client import RealtimeTranscribeClient
from app import OPENAI_API_KEY
from app.voice_agent import VoiceAgentOpenAI

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


STATIC_FOLDER = Path(__file__).parent.parent / "static"

app = FastAPI()

app.mount("/static", StaticFiles(directory=STATIC_FOLDER.as_posix()), name="static")

# Allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Convert frames to WAV format in memory
def pcm_to_wave(data):
    # Define parameters
    sample_rate = 24000  # Sample rate in Hz
    num_channels = 1  # Mono
    sample_width = 2  # 2 bytes for 16-bit audio

    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, "wb") as wf:
        wf.setnchannels(num_channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(data)

    # Get the WAV data
    wav_buffer.seek(0)
    return wav_buffer.read()


@app.websocket("/ws/audio")
async def websocket_endpoint(websocket: WebSocket):
    """
    client -> stream -> audio_buffer
    async text = stt_handler(audio_buffer)
    async text = llm_handler(text)
    async audio = tts_handler(text)
    audio -> stream -> client
    """
    await websocket.accept()
    session_id = str(uuid.uuid4())
    session_dir = f"data/{session_id}"
    os.makedirs(session_dir, exist_ok=True)

    agent = VoiceAgentOpenAI()

    transcribe_client = RealtimeTranscribeClient(api_key=OPENAI_API_KEY)
    await transcribe_client.connect()

    logger.info(f"Session[{session_id}] start")
    
    # TODO: Refactor, move the following pipeline to the voice agent.
    async def receive_audio_stream_from_client(websocket, transcribe_client):
        audio_buffer = b""
        seq = 0
        audio_in_filepath = os.path.join(session_dir, "{}_{}_16_24kHZ_mono.wav".format(seq, "in"))
    
        # TODO: use  state machine to fine control
        while True:
            message = await websocket.receive()
            # logger.debug(f"message: {message}")

            # TODO: Validate the message
            if "bytes" in message:
                audio_data = message["bytes"]
                audio_buffer += audio_buffer
                # Write audio to file
                # await audio_file.write(audio_buffer)
                # 1. SST start here, use Realtime API to transcribe the ongoing audio, like
                logger.debug(f"SST start...")
                
                # TODO: Should We transfer all the incoming audio to the OpenAI realtime transcription?
                await transcribe_client.stream_audio(audio_data)
                continue

            if "text" in message:
                data = json.loads(message["text"])
     
                if data.get("event") == "end":
                    # TODO: Check input audio

                    # Save input audio to file
                    f = await aiofiles.open(audio_in_filepath, "wb")
                    audio_buffer = pcm_to_wave(audio_buffer)
                    await f.write(audio_buffer)
                    await f.close()

                    logger.info(
                        f"Save audio buffer size[{len(audio_buffer)}] and audio file to [{audio_in_filepath}]"
                    )
                    
                    # Create next
                    audio_buffer =b""
                    seq += 1
                    audio_in_filepath = os.path.join(session_dir, "{}_{}_16_24kHZ_mono.wav".format(seq, "in"))
        
    async def send_audio_stream_to_client(websocket, transcribe_client):
    
        seq = 0
        audio_out_filepath = os.path.join(session_dir, "{}_{}.pcm".format(seq, "out"))
        
        async for transcribed_text in transcribe_client.receive_messages():
            print("transcribed_text:", transcribed_text)
            
            # 2 LLM
            logging.info(f"LLM start...")
            response_text = await agent.call_llm_async(transcribed_text)
            logger.info(f"llm_response_text: {response_text}")
            
            # 3 TTS
            logger.info(f"TTS start...")
            await agent.text_to_speech_streaming_websocket(
                text=response_text, ws=websocket, output_path=audio_out_filepath
            )
            
            seq += 1
            audio_out_filepath = os.path.join(session_dir, "{}_{}.pcm".format(seq, "out"))

                
    try:       
        # await receive_audio_stream_from_client(websocket, transcribe_client)
        # Create background task
        # asyncio.create_task(receive_audio_stream_from_client(websocket, transcribe_client))
        # asyncio.create_task(send_audio_stream_to_client(websocket, transcribe_client))
        # Run send task in foreground
        # await send_audio_stream_to_client(websocket, transcribe_client)
        
        await asyncio.gather(receive_audio_stream_from_client(websocket, transcribe_client), send_audio_stream_to_client(websocket, transcribe_client))
    except Exception as e:
        # TODO: Use customized Exception for STT, LLM, or TTS failures.
        # raise HTTPException(status_code=502, detail=f"STT error: {str(e)}")
        await websocket.close(code=1003, reason=str(e))

    except WebSocketDisconnect:
        logger.info("Client disconnected")

    finally:
        logger.info(f"Session[{session_id}] close")
        await websocket.close()


@app.get("/items/", response_class=HTMLResponse)
async def read_items():
    return """
    <html>
        <head>
            <title>Some HTML in here</title>
        </head>
        <body>
            <h1>Look ma! HTML!</h1>
        </body>
    </html>
    """


@app.get("/client.html")
async def read_root():
    return FileResponse(STATIC_FOLDER.joinpath("client.html"))
