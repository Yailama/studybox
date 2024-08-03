import json
import os
from typing import Union, Dict

import uvicorn
from fastapi import FastAPI, HTTPException, middleware, Request, Response
from pydantic import ValidationError
from .config.logging_config import fastapi_logger as logger

from app import schemas

from .celery_worker import celery_app, evaluate_answer

app = FastAPI()


def load_and_validate_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    try:
        band_descriptors = schemas.BandDescriptors(**json_data)
        return band_descriptors.dict()
    except ValidationError as e:
        logger.error("Unable to load band descriptors file")
        raise HTTPException(status_code=422, detail="JSON validation error") from e


@app.on_event("startup")
async def startup_event():
    file_name = 'band_descriptors.json'
    file_path = os.path.join(os.path.dirname(__file__), file_name)

    try:
        app.band_descriptors = load_and_validate_json(file_path)
    except FileNotFoundError as e:
        logger.error("Unable to load band descriptors file")
        raise HTTPException(status_code=404, detail=f"File '{file_name}' not found.") from e

    file_name = "prompts/band_scores_prompt_template.txt"
    with open(os.path.join(os.path.dirname(__file__), file_name), 'r', encoding='utf-8') as f:
        app.band_score_prompt_template = f.read()

    file_name = "prompts/writing_correction_prompt_template.txt"
    with open(os.path.join(os.path.dirname(__file__), file_name), 'r', encoding='utf-8') as f:
        app.writing_correction_prompt_template = f.read()


@app.middleware("http")
async def log_middleware(request: Request, call_next):
    response: Response = await call_next(request)

    logger.info(
        "Request processed",
        method=request.method,
        url=str(request.url),
        client_ip=request.client.host,
        status_code=response.status_code,
        headers=dict(request.headers),
        response_headers=dict(response.headers)
    )

    return response


@app.post(
    "/evaluate",
    response_model=schemas.TaskRegistration,
)
def register_evaluation_task(eval_item: schemas.AnswerIn):
    celery_task = evaluate_answer(question_type=eval_item.task.question_type,
                                  question_part=eval_item.task.question_part,
                                  question=eval_item.task.question,
                                  answer=eval_item.task.answer,
                                  band_descriptors=app.band_descriptors,
                                  band_score_prompt_template=app.band_score_prompt_template,
                                  writing_correction_prompt_template=app.writing_correction_prompt_template)
    return {"task_id": celery_task}


@app.get("/tasks/{task_id}", response_model=Union[schemas.SpeakingFeedbackOut, schemas.WritingFeedbackOut, Dict[str, str]])
def get_task(task_id: str, response: Response):
    group_result = celery_app.GroupResult.restore(task_id)

    if group_result:
        if not group_result.ready():
            response.status_code = 202
            return {"detail": "Evaluation in progress"}

        if group_result.failed():
            raise HTTPException(status_code=400, detail="A task in the group failed")

        group_result = group_result.get()
        merged_results = {}
        [merged_results.update(task_result) for task_result in group_result]

        return merged_results

    raise HTTPException(status_code=400, detail=f"Task with id {task_id} not found")


def start():
    """Launched with `poetry run start` at root level"""
    uvicorn.run("app.main:start", host="0.0.0.0", port=8000, reload=True)
