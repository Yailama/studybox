import json
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def group_result_mock(data):
    mock_response = MagicMock()
    mock_response.ready = MagicMock(return_value=data["ready"])
    mock_response.successful = MagicMock(return_value=data["successful"])
    mock_response.failed = MagicMock(return_value=data["failed"])
    mock_response.get = MagicMock(return_value=data.get("results", None))
    return mock_response


valid_writing_output = {
    "Task Achievement": {
      "score": 4,
      "feedback": "Feedback here."
    },
    "Coherence & Cohesion": {
      "score": 4,
      "feedback": "Feedback here."
    },
    "Lexical Resource": {
      "score": 4,
      "feedback": "Feedback here."
    },
    "Grammatical Range & Accuracy": {
      "score": 5,
      "feedback": "Feedback here."
    },
    "Text Correction": [
      {
        "type": "strength",
        "subtype": "spelling",
        "source": "initial sentence",
        "content": "some comment here",
      },
      {
        "type": "mistake",
        "subtype": "spelling",
        "source": "initial sentence",
        "content": "some comment here",
        "difference": [{"before": "wrong", "after": "right"}]
      },
      {
        "type": "mistake",
        "subtype": "spelling",
        "source": "initial sentence",
        "content": "some comment here",
        "difference": [{"before": "wrong", "after": "right"}]
      }
    ]
  }

valid_writing_celery_output = [
    {
        "Task Achievement": {
            "score": 4,
            "feedback": "Feedback here."
        }
    },
    {
        "Coherence & Cohesion": {
            "score": 4,
            "feedback": "Feedback here."
        }
    },
    {
        "Lexical Resource": {
            "score": 4,
            "feedback": "Feedback here."
        }
    },
    {
        "Grammatical Range & Accuracy": {
            "score": 5,
            "feedback": "Feedback here."
        }
    },
    {
        "Text Correction": [
            {
                "type": "strength",
                "subtype": "spelling",
                "source": "initial sentence",
                "content": "some comment here",
            },
            {
                "type": "mistake",
                "subtype": "spelling",
                "source": "initial sentence",
                "content": "some comment here",
                "difference": [{"before": "wrong", "after": "right"}]
            },
            {
                "type": "mistake",
                "subtype": "spelling",
                "source": "initial sentence",
                "content": "some comment here",
                "difference": [{"before": "wrong", "after": "right"}]
            }
        ]
    }
]

valid_speaking_output = {
    "Fluency and Coherence": {
      "score": 4,
      "feedback": "Feedback here."
    },
    "Lexical Resource": {
      "score": 4,
      "feedback": "Feedback here."
    },
    "Grammatical Range & Accuracy": {
      "score": 5,
      "feedback": "Feedback here."
    }
  }

valid_speaking_celery_output = [
    {
        "Fluency and Coherence": {
            "score": 4,
            "feedback": "Feedback here."
        }
    },
    {
        "Lexical Resource": {
            "score": 4,
            "feedback": "Feedback here."
        }
    },
    {
        "Grammatical Range & Accuracy": {
            "score": 5,
            "feedback": "Feedback here."
        }
    }
]

test_data = [
    ({
        "ready": False,
        "successful": True,
        "failed": False
    }, 202, {"detail": "Evaluation in progress"}),
    ({
        "ready": True,
        "successful": False,
        "failed": True
    }, 400, {"detail": "A task in the group failed"}),
    ({
        "ready": True,
        "successful": True,
        "failed": False,
        "results": valid_writing_celery_output
    }, 200, valid_writing_output),
    ({
         "ready": True,
         "successful": True,
         "failed": False,
         "results": valid_speaking_celery_output
     }, 200, valid_speaking_output)
]


@pytest.fixture
def set_group_result_mock(group_result):
    with patch('app.celery_worker.celery_app.GroupResult.restore') as mock_group_result:
        mock_group_result.return_value = group_result_mock(group_result)
        yield mock_group_result
@pytest.mark.parametrize("group_result, status_code, message", test_data)
def test_get_task_result(set_group_result_mock, group_result, status_code, message):

    response = client.get("/tasks/test-task-id")
    assert response.status_code == status_code
    assert json.loads(response.text) == message
