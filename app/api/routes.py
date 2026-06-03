import os
import uuid
from fastapi import APIRouter, HTTPException
from app.api.schemas import PreprocessRequest, PreprocessResponse
from app.services.pipeline import PreprocessingPipeline

router = APIRouter()
OUTPUT_BASE = os.environ.get("OUTPUT_DIR", "data/api_outputs")

pipeline = PreprocessingPipeline()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/preprocess", response_model=PreprocessResponse)
def preprocess(request: PreprocessRequest):
    image_path = request.image
    boundary_path = request.boundary

    if not os.path.exists(image_path):
        raise HTTPException(status_code=400, detail=f"Image not found: {image_path}")
    if not os.path.exists(boundary_path):
        raise HTTPException(status_code=400, detail=f"Boundary not found: {boundary_path}")

    run_id = uuid.uuid4().hex[:8]
    output_dir = f"{OUTPUT_BASE}/{run_id}"
    os.makedirs(output_dir, exist_ok=True)

    try:
        result = pipeline.run(
            raster_path=image_path,
            boundary_path=boundary_path,
            output_dir=output_dir,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return PreprocessResponse(
        status=result["status"],
        output_dir=output_dir,
        ndvi=result.get("ndvi_path", ""),
        steps=result.get("steps", []),
    )
