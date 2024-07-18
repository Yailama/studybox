import json
import os

import uvicorn
from celery.result import AsyncResult
from fastapi import FastAPI, HTTPException
from pydantic import ValidationError

from app import schemas
from .schemas import BandDescriptors

from .celery_worker import celery_app, evaluate_answer


app = FastAPI()


def load_and_validate_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    try:
        band_descriptors = BandDescriptors(**json_data)
        return band_descriptors.dict()
    except ValidationError as e:
        raise HTTPException(status_code=422, detail="JSON validation error") from e

# Define startup event function
@app.on_event("startup")
async def startup_event():
    file_name = 'band_descriptors.json'
    file_path = os.path.join(os.path.dirname(__file__), file_name)

    try:
        app.band_descriptors = load_and_validate_json(file_path)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"File '{file_name}' not found.") from e

    file_name="prompts/band_scores_prompt_template.txt"
    with open(os.path.join(os.path.dirname(__file__), file_name), 'r', encoding='utf-8') as f:
        app.band_score_prompt_template = f.read()

    file_name="prompts/writing_correction_prompt_template.txt"
    with open(os.path.join(os.path.dirname(__file__), file_name), 'r', encoding='utf-8') as f:
        app.writing_correction_prompt_template = f.read()


@app.post(
    "/evaluate",
    response_model=schemas.TaskRegistration,
)
def register_evaluation_task(eval_item: schemas.AnswerIn):
    celery_task = evaluate_answer.delay(question_type=eval_item.task.question_type,
                                        question_part=eval_item.task.question_part,
                                        question=eval_item.task.question,
                                        answer=eval_item.task.answer,
                                        band_descriptors=app.band_descriptors,
                                        band_score_prompt_template=app.band_score_prompt_template,
                                        writing_correction_prompt_template=app.writing_correction_prompt_template)
    return {"task_id": celery_task.id}


@app.get("/tasks/{task_id}")
def get_task(task_id: str):
    result = AsyncResult(task_id, app=celery_app)

    if result.ready():
        return {"status": "Task completed!", "result": result.result}
    return {"status": "Task pending or in progress.", "result": result.result}


def start():
    """Launched with `poetry run start` at root level"""
    uvicorn.run("app.main:start", host="0.0.0.0", port=8000, reload=True)
