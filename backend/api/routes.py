import asyncio
import uuid
import os
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import FileResponse
from typing import Optional

from backend.api.schemas import TaskInfo, ModelInfo, ExplainerInfo, JobStatus
from backend.tasks import get_task_handler, list_tasks
from backend.core.image_utils import load_and_validate_image
from backend.core.job_manager import create_job, get_job, store_uploaded_data, VISUALIZATION_DIR
from backend.core.pipeline import run_explanation_pipeline

router = APIRouter(prefix="/api")

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


@router.get("/tasks", response_model=list[TaskInfo])
async def get_tasks():
    return [TaskInfo(**t) for t in list_tasks()]


@router.get("/models", response_model=list[ModelInfo])
async def get_models(task: str = Query(...)):
    handler = get_task_handler(task)
    return [ModelInfo(**m) for m in handler.get_models()]


@router.get("/explainers", response_model=list[ExplainerInfo])
async def get_explainers(task: str = Query(...), model: Optional[str] = Query(None)):
    handler = get_task_handler(task)
    model_name = model or (handler.get_models()[0]["name"] if handler.get_models() else "")
    return [ExplainerInfo(**e) for e in handler.get_explainers(model_name)]


@router.post("/explain")
async def explain(
    task: str = Query(...),
    model_name: str = Query(...),
    explainer_names: str = Query(..., description="Comma-separated explainer names"),
    ranking_metric: str = Query("average", description="Metric for ranking: average, mu_fidelity, abpc, sensitivity, complexity"),
    file: UploadFile = File(...),
):
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB.")

    # Validate task
    try:
        handler = get_task_handler(task)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Process input based on task
    if task == "image":
        try:
            data = load_and_validate_image(contents)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    elif task == "text":
        data = contents.decode("utf-8", errors="replace")
    elif task == "timeseries":
        data = contents
    else:
        raise HTTPException(status_code=400, detail=f"Unknown task: {task}")

    # Parse explainer names
    names = [n.strip() for n in explainer_names.split(",") if n.strip()]
    if not names:
        raise HTTPException(status_code=400, detail="At least one explainer must be selected.")

    # Normalize ranking metric - default to "average" if invalid or missing
    valid_metrics = ("average", "mu_fidelity", "abpc", "sensitivity", "complexity")
    if ranking_metric not in valid_metrics:
        ranking_metric = "average"

    # Create job
    job_id = str(uuid.uuid4())
    store_uploaded_data(job_id, data, task)
    create_job(job_id, task, model_name, names, ranking_metric)

    # Run pipeline in thread pool executor
    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, run_explanation_pipeline, job_id, task, model_name, names, ranking_metric, {})

    return {"job_id": job_id}


@router.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return job


@router.get("/jobs/{job_id}/visualizations/{explainer_name}.png")
async def get_visualization(job_id: str, explainer_name: str):
    viz_path = os.path.join(VISUALIZATION_DIR, job_id, f"{explainer_name}.png")
    if not os.path.exists(viz_path):
        raise HTTPException(status_code=404, detail="Visualization not found.")
    return FileResponse(viz_path, media_type="image/png")


@router.get("/jobs/{job_id}/original/{filename}")
async def get_original_data(job_id: str, filename: str):
    file_path = os.path.join(VISUALIZATION_DIR, job_id, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Original data not found.")

    if filename.endswith(".png"):
        return FileResponse(file_path, media_type="image/png")
    elif filename.endswith(".txt"):
        return FileResponse(file_path, media_type="text/plain")
    elif filename.endswith(".csv"):
        return FileResponse(file_path, media_type="text/csv")
    return FileResponse(file_path)
