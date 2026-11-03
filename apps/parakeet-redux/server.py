import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse
from kestrel.config import RuntimeConfig
from kestrel.engine import InferenceEngine

MODEL = "moondream/parakeet-redux"
MAX_AUDIO_BYTES = 64 * 1024 * 1024
logger = logging.getLogger("parakeet-redux")


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = await InferenceEngine.create(
        RuntimeConfig(model=MODEL, device="cpu", cpu_threads=8, max_batch_size=4)
    )
    app.state.model = engine.model(MODEL)
    try:
        yield
    finally:
        await engine.shutdown()


app = FastAPI(title="Parakeet Redux transcription API", lifespan=lifespan)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


def format_timestamp(seconds: float, separator: str) -> str:
    millis = round(seconds * 1000)
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    seconds, millis = divmod(millis, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02}{separator}{millis:03}"


def format_subtitles(segments: list[dict], response_format: str) -> str:
    separator = "." if response_format == "vtt" else ","
    cues = []
    for index, segment in enumerate(segments, start=1):
        start = format_timestamp(segment["start"], separator)
        end = format_timestamp(segment["end"], separator)
        cues.append(f"{index}\n{start} --> {end}\n{segment['text'].strip()}")
    content = "\n\n".join(cues)
    return f"WEBVTT\n\n{content}" if response_format == "vtt" else content


@app.post("/v1/audio/transcriptions")
async def transcribe(
    request: Request,
    file: UploadFile = File(...),
    model: str = Form(...),
    response_format: str = Form("json"),
):
    del model  # LiteLLM selects this deployment by its public model name.
    if response_format not in {"json", "text", "verbose_json", "srt", "vtt"}:
        raise HTTPException(status_code=400, detail="Unsupported response_format")

    audio = await file.read(MAX_AUDIO_BYTES + 1)
    if not audio:
        raise HTTPException(status_code=400, detail="Audio file is empty")
    if len(audio) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Audio files are limited to 64 MiB")

    try:
        result = await request.app.state.model.transcribe(
            audio=audio,
            timestamps="segment",
        )
    except Exception as exc:
        logger.exception("Parakeet transcription failed")
        raise HTTPException(status_code=500, detail="Transcription failed") from exc

    output = result.output
    text = output["text"]
    if response_format == "text":
        return PlainTextResponse(text)
    if response_format in {"srt", "vtt"}:
        return PlainTextResponse(
            format_subtitles(output.get("segments", []), response_format),
            media_type="text/vtt" if response_format == "vtt" else "application/x-subrip",
        )
    if response_format == "verbose_json":
        return JSONResponse(
            {
                "text": text,
                "task": "transcribe",
                "language": output.get("language"),
                "segments": output.get("segments", []),
            }
        )
    return JSONResponse({"text": text})
