import json
import os
from json import JSONDecodeError
from typing import Union, Dict

import uvicorn
from celery.result import AsyncResult

from fastapi import FastAPI, HTTPException, Request, Response, File, UploadFile, Form
from pydantic import ValidationError
from app import schemas

from .config.logging_config import fastapi_logger as logger
from .celery_worker import celery_app, WritingAnswerEvaluator, SpeakingAnswerEvaluator

app = FastAPI()


def load_and_validate_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        try:
            json_data = json.load(f)
        except JSONDecodeError:
            logger.error("Invalid JSON")
            raise
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

    file_name = "prompts/writing_final_score_prompt_template.txt"
    with open(os.path.join(os.path.dirname(__file__), file_name), 'r', encoding='utf-8') as f:
        app.writing_final_score_prompt_template = f.read()

    file_name = "prompts/speaking_final_score_prompt_template.txt"
    with open(os.path.join(os.path.dirname(__file__), file_name), 'r', encoding='utf-8') as f:
        app.speaking_final_score_prompt_template = f.read()


@app.middleware("http")
async def log_middleware(request: Request, call_next):
    response: Response = await call_next(request)

    logger.info(
        "Request processed",
        method=request.method,
        url=str(request.url),
        client_ip=request.client.host,
        status_code=response.status_code,
        # headers=dict(request.headers),
        # response_headers=dict(response.headers)
    )

    return response

@app.post(
    "/evaluate/writing",
    response_model=schemas.TaskRegistration,
)
def register_writing_evaluation_task(eval_item: schemas.AnswerIn):
    answer_evaluator = WritingAnswerEvaluator(
                                  question_type="writing",
                                  question_part=eval_item.task.question_part,
                                  question=eval_item.task.question,
                                  answer=eval_item.task.answer,
                                  band_descriptors=app.band_descriptors,
                                  band_score_prompt_template=app.band_score_prompt_template,
                                  final_score_prompt_template=app.writing_final_score_prompt_template)

    celery_task = answer_evaluator.register_evaluation_task()
    return {"task_id": celery_task}


@app.post(
    "/evaluate/speaking",
    response_model=schemas.TaskRegistration,)
def register_speaking_evaluation_task(question: str = Form(...), file: UploadFile = File()):
    answer_evaluator = SpeakingAnswerEvaluator(
        question_type="speaking",
        question_part="1",
        question=question,
        answer=file,
        band_descriptors=app.band_descriptors,
        band_score_prompt_template=app.band_score_prompt_template,
        final_score_prompt_template=app.speaking_final_score_prompt_template)

    celery_task = answer_evaluator.register_evaluation_task()
    return {"task_id": celery_task}


@app.get("/tasks/{task_id}",
         response_model=Union[schemas.SpeakingFeedbackOut,
         schemas.WritingFeedbackOut, Dict[str, str]])
def get_task(task_id: str, response: Response):
    chord_result = AsyncResult(task_id, app=celery_app)

    if chord_result.ready():
        if chord_result.successful():
            final_result = chord_result.result

            merged_results = {}
            [merged_results.update(result) for result in final_result]
            return merged_results
    response.status_code = 202
    return {"detail": "Pending"}

def start():
    """Launched with `poetry run start` at root level"""
    uvicorn.run("app.main:start", host="0.0.0.0", port=8000, reload=True)
