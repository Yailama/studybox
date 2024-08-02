import json
from unittest.mock import patch, MagicMock
import pytest
import os

from app import celery_worker
from app.celery_worker import AnswerEvaluator, Prompt, InvalidResponseFormat, evaluate_answer

import openai

os.environ["OPENAI_API_KEY"] = "DUMMY_KEY"

descriptors = {
    "descriptors": [
        {
            "name": "Coherence & Cohesion",
            "scores": {
                "9": "The message can be followed effortlessly. Cohesion is used in such a way that it very rarely attracts attention. Any lapses in coherence or cohesion are minimal. Paragraphing is skilfully managed.",
                "8": "The message can be followed with ease. Information and ideas are logically sequenced, and cohesion is well managed. Occasional lapses in coherence and cohesion may occur. Paragraphing is used sufficiently and appropriately.",
                "7": "Information and ideas are logically organised, and there is a clear progression throughout the response. (A few lapses may occur, but these are minor.) A range of cohesive devices including reference and substitution is used flexibly but with some inaccuracies or some over/under use. Paragraphing is generally used effectively to support overall coherence, and the sequencing of ideas within a paragraph is generally logical.",
                "6": "Information and ideas are generally arranged coherently and there is a clear overall progression. Cohesive devices are used to some good effect but cohesion within and/or between sentences may be faulty or mechanical due to misuse, overuse or omission. The use of reference and substitution may lack flexibility or clarity and result in some repetition or error. Paragraphing may not always be logical and/or the central topic may not always be clear.",
                "5": "Organisation is evident but is not wholly logical and there may be a lack of overall progression. Nevertheless, there is a sense of underlying coherence to the response. The relationship of ideas can be followed but the sentences are not fluently linked to each other. There may be limited/overuse of cohesive devices with some inaccuracy. The writing may be repetitive due to inadequate and/or inaccurate use of reference and substitution. Paragraphing may be inadequate or missing.",
                "4": "Information and ideas are evident but not arranged coherently and there is no clear progression within the response. Relationships between ideas can be unclear and/or inadequately marked. There is some use of basic cohesive devices, which may be inaccurate or repetitive. There is inaccurate use or a lack of substitution or referencing. There may be no paragraphing and/or no clear main topic within paragraphs.",
                "3": "There is no apparent logical organisation. Ideas are discernible but difficult to relate to each other. There is minimal use of sequencers or cohesive devices. Those used do not necessarily indicate a logical relationship between ideas. There is difficulty in identifying referencing. Any attempts at paragraphing are unhelpful.",
                "2": "There is little relevant message, or the entire response may be off-topic. There is little evidence of control of organisational features.",
                "1": "Responses of 20 words or fewer are rated at Band 1. The writing fails to communicate any message and appears to be by a virtual non-writer.",
                "0": "Should only be used where a candidate did not attend or attempt the question in any way, used a language other than English throughout, or where there is proof that a candidate’s answer has been totally memorised."
            }
        }
    ]
}


def chat_completion_mock(data):
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content=data
            )
        )
    ]
    return mock_response


@pytest.fixture
def set_chat_completion_mock(chat_completion_result):
    with patch('openai.chat.completions.create') as mock_create:
        mock_create.return_value = chat_completion_mock(chat_completion_result)
        yield mock_create


valid_response = (
    json.dumps(
        {"feedback": "This is the mocked feedback", "score": 9}),
    {'Coherence & Cohesion': {'feedback': 'This is the mocked feedback', 'score': 9}},
    False
)

invalid_json_response = (
    json.dumps({"feedback": "Missing score"}),
    None,
    True
)

not_a_json_response = (
    "this is not a JSON string",
    None,
    True
)


@pytest.mark.parametrize("chat_completion_result, expected_result, should_raise", [valid_response, invalid_json_response, not_a_json_response])
def test_prompt_response(set_chat_completion_mock, chat_completion_result, expected_result, should_raise):
    prompt = Prompt(
            prompt_message="dummy message",
            response_type="Score and Feedback",
            band_descriptor="Coherence & Cohesion",
            response_format="json_object",
            answer="answer")

    if should_raise:
        with pytest.raises(InvalidResponseFormat):
            celery_worker.get_feedback(prompt=prompt.to_dict())
    else:
        result = celery_worker.get_feedback(prompt=prompt.to_dict())
        assert result == expected_result