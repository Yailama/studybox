import json
import logging
import os
import re
import io
from abc import ABC, abstractmethod
from enum import Enum
from json import JSONDecodeError
from typing import Dict, Any

from celery import Celery, group
from celery import signals
import openai
from openai import OpenAIError, RateLimitError, AuthenticationError
import structlog
from fastapi import UploadFile
from pydantic import ValidationError

from app.schemas import WritingTextCorrectionFeedback, BandDescriptorFeedback
from .config.logging_config import celery_logger as logger


openai.api_key = os.getenv("OPENAI_KEY")
REDIS_BROKER = os.getenv("REDIS_BROKER")
REDIS_BACKEND = os.getenv("REDIS_BACKEND")
SEED = 1
COMPLETION_TOKENS = 1500  # 2500
MAX_TOKENS = 3000  # 4050
GPT_MODEL = os.getenv("GPT_MODEL")


@signals.setup_logging.connect
def supress(**kwargs):
    logger = logging.getLogger()
    for handler in logger.handlers:
        handler.setFormatter(StructlogFormatter())


celery_app = Celery(
    "celery_worker",
    broker=REDIS_BROKER,
    backend=REDIS_BACKEND,
    broker_connection_retry_on_startup=True
)


class StructlogFormatter(logging.Formatter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.processor = structlog.processors.JSONRenderer()

    def format(self, record):
        log_dict = {
            'component': "celery_app",
            'event': record.getMessage(),
            'level': record.levelname.lower(),
            'timestamp': self.formatTime(record, self.datefmt),
            'logger': record.name
        }

        if re.match("celery.*", record.name) and "return_value" in record.args:
            try:
                return_value = record.args["return_value"]
                message_as_json = json.loads(re.sub("'", "\"", return_value))
                if isinstance(message_as_json, dict):
                    log_dict['data'] = message_as_json
                    record.args["return_value"] = "see data section for returned JSON"
                    log_dict['event'] = record.getMessage()
            except (json.JSONDecodeError, TypeError):
                log_dict["event"] = return_value
        return json.dumps(log_dict)

@signals.task_prerun.connect
def on_task_prerun(sender, task_id, task, args, kwargs, **_):
    structlog.contextvars.bind_contextvars(task_id=task_id, task_name=task.name)


class FeedbackType(Enum):
    SCORE_AND_EXPLANATION = "Score and Feedback"
    TEXT_CORRECTION = "Text Correction"


class ResponseFormat(Enum):
    TEXT = "text"
    JSON_OBJECT = "json_object"


class QuestionType(Enum):
    SPEAKING = "speaking"
    WRITING = "writing"


class MaxRetriesExceededError(Exception):
    pass


class InvalidResponseFormat(Exception):
    """Invalid response format, expected '[0-9] - explanation"""
    pass


class FileReadError(Exception):
    """Unable to read audio file and put in BytesIO"""
    pass


class NonRetryableError(Exception):
    """Error on which task should not be retried"""
    pass


@celery_app.task(bind=True,
                 autoretry_for=(InvalidResponseFormat,),
                 retry_backoff=True,
                 retry_kwargs={'max_retries': 5}
                 )
def get_feedback(self, prompt):
    if self.request.retries > 0:
        prompt.seed += 1
    feedback = gpt_feedback_request(prompt=prompt)
    return feedback


def transcribe_audio(file: UploadFile):
    try:
        audio_contents = file.file.read()
        buffer = io.BytesIO(audio_contents)
        buffer.name = file.filename
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        raise NonRetryableError(f"Error reading file: {e}") from e

    try:
        answer = openai.audio.transcriptions.create(file=buffer, model="whisper-1",
                                                    response_format="text")
        return answer
    except RateLimitError as e:
        logger.error(f"Rate limit error: {e}")
        raise NonRetryableError(f"Rate limit error: {e}") from e
    except AuthenticationError as e:
        logger.error(f"Authentication error: {e}")
        raise NonRetryableError(f"Authentication error: {e}") from e
    except OpenAIError as e:
        logger.error(f"OpenAI error occurred: {e}")
        raise


class Prompt:
    def __init__(self, prompt_message: str, response_type: str,
                 band_descriptor: str, response_format: str, answer: str):
        self.prompt_message = prompt_message
        self.response_type = response_type
        self.band_descriptor = band_descriptor
        self.response_format = response_format
        self.answer = answer
        self.seed = SEED

    def to_dict(self):
        return {
            "prompt_message": self.prompt_message,
            "response_type": self.response_type,
            "band_descriptor": self.band_descriptor,
            "response_format": self.response_format,
            "answer": self.answer,
            "seed": self.seed,
        }

    def to_json(self):
        return json.dumps(self.to_dict())


class BaseAnswerEvaluator(ABC):
    def __init__(self, question_part: str, question_type: QuestionType,
                 question: str, answer: str | UploadFile,
                 band_descriptors: Dict, band_score_prompt_template: str):
        self.question = question
        self.question_part = question_part
        self.answer = answer
        self.feedback = {}
        self.question_type = question_type
        self.band_descriptors = band_descriptors
        self.band_score_prompt_template = band_score_prompt_template

    @abstractmethod
    def get_prompts(self):
        descriptors = self.band_descriptors["sections"][self.question_type]["parts"][self.question_part]["descriptors"]

        prompts = [
            Prompt(
                prompt_message=self.band_score_prompt_template.format(
                    question_type=self.question_type,
                    question_part=self.question_part,
                    question=self.question,
                    criteria_name=x['name'],
                    scores_description=x['scores']
                ),
                response_type=FeedbackType.SCORE_AND_EXPLANATION.value,
                band_descriptor=x['name'],
                response_format=ResponseFormat.JSON_OBJECT.value,
                answer=self.answer
            ) for x in descriptors
        ]

        return prompts

    def register_evaluation_task(self):
        prompts = self.get_prompts()
        feedback_tasks = [get_feedback.s(prompt.to_dict()) for prompt in prompts]
        result = group(feedback_tasks).apply_async()
        result.save()
        return result.id


class WritingAnswerEvaluator(BaseAnswerEvaluator):

    def __init__(self, question_part: str, question_type: QuestionType,
                 question: str, answer: str,
                 band_descriptors: Dict, band_score_prompt_template: str,
                 writing_correction_prompt_template: str):
        super().__init__(question_part, question_type, question, answer, band_descriptors,
                         band_score_prompt_template)
        self.writing_correction_prompt_template = writing_correction_prompt_template

    def get_prompts(self):
        prompts = super().get_prompts()
        prompts.append(Prompt(
            prompt_message=self.writing_correction_prompt_template.format(question_part=self.question_part),
            response_type=FeedbackType.TEXT_CORRECTION.value,
            band_descriptor="Text Correction",
            response_format=ResponseFormat.JSON_OBJECT.value,
            answer=self.answer))

        return prompts


class SpeakingAnswerEvaluator(BaseAnswerEvaluator):

    def __init__(self, question_part: str, question_type: QuestionType,
                 question: str, answer: UploadFile,
                 band_descriptors: Dict, band_score_prompt_template: str):
        super().__init__(question_part, question_type, question, answer, band_descriptors,
                         band_score_prompt_template)

    def get_prompts(self):
        return super().get_prompts()

    def register_evaluation_task(self):
        answer = transcribe_audio(file=self.answer)
        self.answer = answer
        return super().register_evaluation_task()


def gpt_feedback_request(prompt):
    response = openai.chat.completions.create(
        model=GPT_MODEL,
        messages=[
            {
                "role": "system",
                "content": prompt["prompt_message"]
            },
            {
                "role": "user",
                "content": prompt["answer"]
            }
        ],
        temperature=1,
        max_tokens=COMPLETION_TOKENS,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
        seed=prompt["seed"],
        response_format={"type": prompt["response_format"]}
    )
    response = response.choices[0].message.content
    feedback = answer_validation(response, prompt)
    return {prompt["band_descriptor"]: feedback}


def answer_validation(response: Any, prompt: Prompt):
    if prompt["response_type"] == FeedbackType.SCORE_AND_EXPLANATION.value:
        try:
            feedback = BandDescriptorFeedback(**json.loads(response)).model_dump()
        except ValidationError as e:
            logger.error(f"Invalid response format for Band Descriptor Feedback: {response}. "
                         f"Trace: {str(e)}")
            raise InvalidResponseFormat from e
        except JSONDecodeError as e:
            logger.error("Not valid JSON for OpenAI response")
            raise InvalidResponseFormat from e
        except Exception as e:
            logger.error(f"Unexpected exception occurred. Trace: {str(e)}")
            raise
    if prompt["response_type"] == FeedbackType.TEXT_CORRECTION.value:
        try:
            feedback = WritingTextCorrectionFeedback(**json.loads(response)).model_dump()["feedback"]
        except Exception as e:
            logger.error(f"Invalid response format for Writing Text Correction: {response}. "
                         f"Trace: {str(e)}")
            raise
    return feedback
