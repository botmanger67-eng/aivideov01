import os
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import asyncio

# Import the video generation pipeline (assumed to exist)
from pipeline import generate_video

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AutoShorts Generator", version="1.0.0")

# Ensure required directories exist
Path("static").mkdir(exist_ok=True)
Path("output").mkdir(exist_ok=True)

# Mount static files (CSS, JS, images, index.html)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Mount output directory for generated videos
app.mount("/output", StaticFiles(directory="output"), name="output")


@app.on_event("startup")
async def startup_event():
    """Check that required API keys are set."""
    required_keys = ["DEEPSEEK_API_KEY", "ELEVENLABS_API_KEY", "PIXABAY_API_KEY"]
    missing = [k for k in required_keys if not os.getenv(k)]
    if missing:
        logger.error(f"Missing environment variables: {', '.join(missing)}. Video generation will fail.")
        # Optionally raise an exception to stop the app; but better to let it run and return error to user.
        # raise RuntimeError(f"Missing secrets: {missing}")
    else:
        logger.info("All required API keys are set.")
    logger.info("Application startup complete.")


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the main web UI."""
    index_path = Path("static/index.html")
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found. Please ensure static/index.html exists.")
    return FileResponse(index_path)


@app.get("/favicon.ico")
async def favicon():
    """Return a 204 No Content for favicon requests to avoid 404 errors."""
    return HTMLResponse(content="", status_code=204)


@app.post("/generate")
async def generate_video_endpoint(request: Request, prompt: str = Form(..., min_length=1, max_length=500)):
    """
    Generate a short video based on the given prompt.
    This endpoint runs the generation pipeline asynchronously.
    """
    # Optional: basic prompt validation
    prompt = prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")
    
    logger.info(f"Video generation requested: '{prompt[:50]}...'")

    try:
        # Run CPU-intensive video generation in a thread to keep the event loop free
        # generate_video is expected to return the path to the generated video file (e.g., "output/video_xyz.mp4")
        video_path = await asyncio.to_thread(generate_video, prompt)
        
        # The returned path should be relative to our mounted /output directory
        video_filename = Path(video_path).name
        video_url = f"/output/{video_filename}"
        
        logger.info(f"Video generated successfully: {video_url}")
        return {"video_url": video_url}
        
    except Exception as e:
        logger.exception("Video generation failed")
        raise HTTPException(status_code=500, detail=f"Video generation error: {str(e)}")