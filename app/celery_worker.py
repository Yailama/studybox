import os
import re
from enum import Enum
from typing import Type, Dict

from celery import Celery
import openai


openai.api_key = os.getenv("OPENAI_KEY")
REDIS_BROKER = os.getenv("REDIS_BROKER")
REDIS_BACKEND = os.getenv("REDIS_BACKEND")
SEED = 1

COMPLETION_TOKENS = 800
MAX_TOKENS = 4050
GPT_MODEL = os.getenv("GPT_MODEL")

celery_app = Celery(
    "celery_worker",
    broker=REDIS_BROKER,
    backend=REDIS_BACKEND
)


class FeedbackType(Enum):
    SCORE_AND_EXPLANATION = "score_and_feedback"
    TEXT_CORRECTION = "text_correction"


class FeedbackPattern(Enum):
    SCORE_AND_EXPLANATION = "\d - .*"
    TEXT_CORRECTION = "<div>.*</div>"


class QuestionType(Enum):
    SPEAKING = "speaking"
    WRITING = "writing"


@celery_app.task
def add(x, y):
    return x + y


@celery_app.task
def get_feedback(answer_evaluator, prompt):
    answer_evaluator.gpt_request(prompt)
    return answer_evaluator.feedback


@celery_app.task
def evaluate_answer(question_type: Type[QuestionType],
                    question_part: str,
                    question: str,
                    answer: str,
                    band_descriptors: Dict,
                    band_score_prompt_template: str,
                    writing_correction_prompt_template: str):
    answer_evaluator = AnswerEvaluator(question_part, question_type, question,
                                       answer, band_descriptors, band_score_prompt_template,
                                       writing_correction_prompt_template)
    prompts = answer_evaluator.get_prompts()
    for prompt in prompts:
        get_feedback(answer_evaluator, prompt)
    return answer_evaluator.feedback


class InvalidResponseFormat(Exception):
    "Invalid response format, expected '[0-9] - explanation"
    pass


class Prompt:
    def __init__(self, prompt_message: str, response_type: Type[FeedbackType],
                 band_descriptor: str):
        self.prompt_message = prompt_message
        self.response_type = response_type
        self.band_descriptor = band_descriptor


class AnswerEvaluator:

    def __init__(self, question_part: str, question_type: Type[QuestionType],
                 question: str, answer: str,
                 band_descriptors: Dict, band_score_prompt_template: str,
                 writing_correction_prompt_template: str):
        self.question = question
        self.question_part = question_part
        self.answer = answer
        self.feedback = {}
        self.question_type = question_type

        self.band_descriptors = band_descriptors
        self.band_score_prompt_template = band_score_prompt_template
        self.writing_correction_prompt_template = writing_correction_prompt_template

    def evaluate_answer(self):
        prompts = self.get_prompts()
        for prompt in prompts:
            self.gpt_request(prompt)

    def gpt_request(self, prompt):
        response = openai.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt.prompt_message
                }
            ],
            temperature=1,
            max_tokens=COMPLETION_TOKENS,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            seed=SEED
        )
        response = response.choices[0].message.content
        self.answer_validation(response, prompt)

    def get_prompts(self):

        descriptors = self.band_descriptors["sections"][self.question_type]["parts"][self.question_part]["descriptors"]

        prompts = [
            Prompt(
                prompt_message=self.band_score_prompt_template.format(
                    question_type=self.question_type,
                    question_part=self.question_part,
                    question=self.question,
                    answer=self.answer,
                    criteria_name=x['name'],
                    scores_description=x['scores']
                ),
                response_type=FeedbackType.SCORE_AND_EXPLANATION,
                band_descriptor=x['name']
            ) for x in descriptors
        ]

        prompts.append(Prompt(
            prompt_message=self.writing_correction_prompt_template.format(question_part=self.question_part,
                                                                          answer=self.answer),
            response_type=FeedbackType.TEXT_CORRECTION,
            band_descriptor="text_correction"))

        return prompts

    def answer_validation(self, response: str, prompt: Prompt):
        if prompt.response_type == FeedbackType.SCORE_AND_EXPLANATION:
            if re.match(FeedbackPattern.SCORE_AND_EXPLANATION.value, response) is None:
                raise InvalidResponseFormat
            score = response[0]
            feedback = response[4:]
            self.feedback[prompt.band_descriptor] = {score: feedback}
        if prompt.response_type == FeedbackType.TEXT_CORRECTION:
            self.feedback[prompt.band_descriptor] = response
