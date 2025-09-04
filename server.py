import os
import json
import pathlib
import subprocess
import asyncio
import uuid
from tempfile import NamedTemporaryFile
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from dotenv import load_dotenv
from gtts import gTTS
from tools.list_directory import list_desktop

from smolagents import CodeAgent, DuckDuckGoSearchTool
from gtts_agent import OpenRouterModel

load_dotenv()
app = FastAPI()

ROOT = pathlib.Path(__file__).parent.resolve()
STATIC_DIR = ROOT / "static"
AUDIO_DIR = STATIC_DIR / "audio"
(STATIC_DIR / "characters").mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "assets").mkdir(parents=True, exist_ok=True)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

MODEL = "openai/gpt-oss-20b:free"
search_tool = DuckDuckGoSearchTool()
agent = CodeAgent(
    tools=[search_tool, list_desktop],
    model=OpenRouterModel(MODEL)
)

async def run_agent_blocking(prompt: str) -> str:
    def _run():
        print(f"[Agent] Running prompt: {prompt!r}")
        out = agent.run(prompt)
        if isinstance(out, str) and "Final Answer:" in out:
            out = out.split("Final Answer:")[-1].strip()
        print(f"[Agent] Output length={len(str(out))}")
        return out
    return await asyncio.to_thread(_run)

async def make_tts_and_lipsync(text: str):
    uid = uuid.uuid4().hex
    base = f"assistant_{uid}"
    print(f"[TTS] START uid={uid} text_preview={text[:80]!r}")

    mp3_tmp = NamedTemporaryFile(delete=False, suffix=".mp3")
    mp3_path = mp3_tmp.name
    mp3_tmp.close()

    def _gtts_save():
        print(f"[TTS] Saving MP3 -> {mp3_path}")
        tts = gTTS(text, lang="en")
        tts.save(mp3_path)
    await asyncio.to_thread(_gtts_save)

    wav_path = AUDIO_DIR / f"{base}.wav"
    lipsync_path = AUDIO_DIR / f"{base}_lipsync.json"

    ffmpeg_cmd = ["ffmpeg", "-y", "-i", mp3_path, str(wav_path)]
    print(f"[FFMPEG] Running: {' '.join(ffmpeg_cmd)}")
    try:
        await asyncio.to_thread(subprocess.check_output, ffmpeg_cmd, stderr=subprocess.STDOUT)
        print(f"[FFMPEG] Created WAV: {wav_path}")
    except subprocess.CalledProcessError as e:
        out = e.output.decode() if getattr(e, "output", None) else str(e)
        print(f"[FFMPEG] Failed: {out}")
        raise
    dialog_tmp = NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8")
    dialog_tmp.write(text)
    dialog_tmp.close()
    dialog_path = dialog_tmp.name
    
    rhubarb_cmd = [
        "rhubarb",
        "-f", "json",
        str(wav_path),
        "--extendedShapes", "GHX",
        "--dialogFile", dialog_path,
        "-o", str(lipsync_path)
    ]
    print(f"[Rhubarb] Running: {' '.join(rhubarb_cmd)}")
    try:
        await asyncio.to_thread(subprocess.check_output, rhubarb_cmd, stderr=subprocess.STDOUT)
        print(f"[Rhubarb] Created lipsync: {lipsync_path}")
    except subprocess.CalledProcessError as e:
        out = e.output.decode() if getattr(e, "output", None) else str(e)
        print(f"[Rhubarb] Failed: {out}")
        try:
            os.remove(mp3_path)
        except Exception:
            pass
        return f"/static/audio/{wav_path.name}", {"mouthCues": []}

    try:
        with open(lipsync_path, "r", encoding="utf-8") as fh:
            lipsync_json = json.load(fh)
    except Exception as e:
        print(f"[Rhubarb] Failed to read JSON: {e}")
        lipsync_json = {"mouthCues": []}

    try:
        os.remove(mp3_path)
    except Exception as e:
        print(f"[Cleanup] Could not remove temp mp3: {e}")

    audio_url = f"/static/audio/{wav_path.name}"
    print(f"[TTS] DONE uid={uid}, audio_url={audio_url}, cues={len(lipsync_json.get('mouthCues', []))}")
    return audio_url, lipsync_json

@app.get("/", response_class=HTMLResponse)
async def index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        print("[HTTP] Serving static/index.html")
        return index_file.read_text(encoding="utf-8")
    return "<html><body><h3>Place your index.html in ./static/index.html</h3></body></html>"

@app.post("/chat")
async def chat_endpoint(req: Request):
    body = await req.json()
    prompt_text = body.get("prompt", "")
    print(f"[Chat] Received prompt (len={len(prompt_text)}): {prompt_text!r}")

    try:
        assistant_text = await run_agent_blocking(prompt_text)
        print(f"[Chat] Agent finished (len={len(assistant_text)})")
    except Exception as e:
        assistant_text = "Error running agent"
        print(f"[Chat] Agent error: {e}")

    try:
        audio_url, lipsync_json = await make_tts_and_lipsync(assistant_text)
    except Exception as e:
        print(f"[Chat] TTS/Lipsync error: {e}")
        audio_url, lipsync_json = None, {"mouthCues": []}
        assistant_text += f"\n\n(Attachment generation failed: {e})"

    assistant_msg = {
        "role": "assistant",
        "text": assistant_text,
        "audio": audio_url,
        "lipsync": lipsync_json
    }
    print(f"[Chat] Returning assistant (audio={audio_url})")
    return JSONResponse({"assistant": assistant_msg})
