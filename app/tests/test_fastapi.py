import json
from unittest.mock import MagicMock, patch

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
    mock_response.result = data.get("results", None)
    return mock_response


valid_writing_output = {
  "Task Achievement": {
    "feedback": "dummy content",
    "recommendation": "dummy content",
    "breakdown": [
      {
        "feedback": "dummy content",
        "recommendation": "dummy content",
        "name": "Addressing the Question",
        "score": 8
      },
      {
        "feedback": "dummy content",
        "recommendation": "dummy content",
        "name": "Overview",
        "score": 7
      },
      {
        "feedback": "dummy content",
        "recommendation": "dummy content",
        "name": "Key Features",
        "score": 8
      }
    ]
  },
  "Coherence & Cohesion": {
    "feedback": "dummy content",
    "recommendation": "dummy content",
    "breakdown": [
      {
        "feedback": "dummy content",
        "recommendation": "dummy content",
        "name": "Cohesion Devices",
        "score": 8
      },
      {
        "feedback": "dummy content",
        "recommendation": "dummy content",
        "name": "Logical Flow of Ideas",
        "score": 7
      },
      {
        "feedback": "dummy content",
        "recommendation": "dummy content",
        "name": "Paragraphing",
        "score": 8
      },
      {
        "feedback": "dummy content",
        "recommendation": "dummy content",
        "name": "Presence of Lapses",
        "score": 8
      }
    ]
  },
  "Lexical Resource": {
    "feedback": "dummy content",
    "recommendation": "dummy content",
    "breakdown": [
      {
        "feedback": "dummy content",
        "recommendation": "dummy content",
        "name": "Range of Vocabulary",
        "score": 7
      },
      {
        "feedback": "dummy content",
        "recommendation": "dummy content",
        "name": "Appropriateness of Vocabulary",
        "score": 8
      },
      {
        "feedback": "dummy content",
        "recommendation": "dummy content",
        "name": "Spelling Accuracy",
        "score": 8
      },
      {
        "feedback": "dummy content",
        "recommendation": "dummy content",
        "name": "Use of Collocations and Phrases",
        "score": 7
      }
    ]
  },
  "Grammatical Range & Accuracy": {
    "feedback": "dummy content",
    "recommendation": "dummy content",
    "breakdown": [
      {
        "feedback": "dummy content",
        "recommendation": "dummy content",
        "name": "Range of Sentence Structures",
        "score": 7
      },
      {
        "feedback": "dummy content",
        "recommendation": "dummy content",
        "name": "Accuracy of Grammar",
        "score": 7
      },
      {
        "feedback": "dummy content",
        "recommendation": "dummy content",
        "name": "Punctuation",
        "score": 7
      },
      {
        "feedback": "dummy content",
        "recommendation": "dummy content",
        "name": "Errors",
        "score": 7
      }
    ]
  },
  "General Feedback": {
    "feedback": "dummy content",
    "recommendation": "dummy content",
    "rewriting": "...",
    "score": 8
  }
}
valid_writing_celery_output = [
  {
    "Task Achievement": {
      "feedback": "dummy content",
      "recommendation": "dummy content",
      "breakdown": [
        {
          "feedback": "dummy content",
          "recommendation": "dummy content",
          "name": "Addressing the Question",
          "score": 8
        },
        {
          "feedback": "dummy content",
          "recommendation": "dummy content",
          "name": "Overview",
          "score": 7
        },
        {
          "feedback": "dummy content",
          "recommendation": "dummy content",
          "name": "Key Features",
          "score": 8
        }
      ],
      "score": 8
    }
  },
  {
    "Coherence & Cohesion": {
      "feedback": "dummy content",
      "recommendation": "dummy content",
      "breakdown": [
        {
          "feedback": "dummy content",
          "recommendation": "dummy content",
          "name": "Cohesion Devices",
          "score": 8
        },
        {
          "feedback": "dummy content",
          "recommendation": "dummy content",
          "name": "Logical Flow of Ideas",
          "score": 7
        },
        {
          "feedback": "dummy content",
          "recommendation": "dummy content",
          "name": "Paragraphing",
          "score": 8
        },
        {
          "feedback": "dummy content",
          "recommendation": "dummy content",
          "name": "Presence of Lapses",
          "score": 8
        }
      ],
      "score": 8
    }
  },
  {
    "Lexical Resource": {
      "feedback": "dummy content",
      "recommendation": "dummy content",
      "breakdown": [
        {
          "feedback": "dummy content",
          "recommendation": "dummy content",
          "name": "Range of Vocabulary",
          "score": 7
        },
        {
          "feedback": "dummy content",
          "recommendation": "dummy content",
          "name": "Appropriateness of Vocabulary",
          "score": 8
        },
        {
          "feedback": "dummy content",
          "recommendation": "dummy content",
          "name": "Spelling Accuracy",
          "score": 8
        },
        {
          "feedback": "dummy content",
          "recommendation": "dummy content",
          "name": "Use of Collocations and Phrases",
          "score": 7
        }
      ],
      "score": 8
    }
  },
  {
    "Grammatical Range & Accuracy": {
      "feedback": "dummy content",
      "recommendation": "dummy content",
      "breakdown": [
        {
          "feedback": "dummy content",
          "recommendation": "dummy content",
          "name": "Range of Sentence Structures",
          "score": 7
        },
        {
          "feedback": "dummy content",
          "recommendation": "dummy content",
          "name": "Accuracy of Grammar",
          "score": 7
        },
        {
          "feedback": "dummy content",
          "recommendation": "dummy content",
          "name": "Punctuation",
          "score": 7
        },
        {
          "feedback": "dummy content",
          "recommendation": "dummy content",
          "name": "Errors",
          "score": 7
        }
      ],
      "score": 7
    }
  },
  {
    "General Feedback": {
      "feedback": "dummy content",
      "recommendation": "dummy content",
      "rewriting": "...",
      "score": 8
    }
  }
]

valid_speaking_output = {
  "Fluency & Coherence": {
    "feedback": "dummy content",
    "recommendation": "dummy content",
    "breakdown": [
      {
        "feedback": "dummy content",
        "recommendation": "dummy content",
        "name": "Fluency",
        "score": 5
      },
      {
        "feedback": "dummy content",
        "recommendation": "dummy content",
        "name": "Coherence",
        "score": 6
      }
    ]
  },
  "Lexical Resource": {
    "feedback": "dummy content",
    "recommendation": "dummy content",
    "breakdown": [
      {
        "feedback": "dummy content",
        "recommendation": "dummy content",
        "name": "Range of Vocabulary",
        "score": 4
      },
      {
        "feedback": "dummy content",
        "recommendation": "dummy content",
        "name": "Appropriateness of Vocabulary",
        "score": 5
      },
      {
        "feedback": "dummy content",
        "recommendation": "dummy content",
        "name": "Idiomatic Language",
        "score": 3
      }
    ]
  },
  "Grammatical Range & Accuracy": {
    "feedback": "dummy content",
    "recommendation": "dummy content",
    "breakdown": [
      {
        "feedback": "dummy content",
        "recommendation": "dummy content",
        "name": "Range of Sentence Structures",
        "score": 3
      },
      {
        "feedback": "dummy content",
        "recommendation": "dummy content",
        "name": "Accuracy of Grammar",
        "score": 3
      },
      {
        "feedback": "dummy content",
        "recommendation": "dummy content",
        "name": "Punctuation and Intonation",
        "score": 3
      }
    ]
  },
  "General Feedback": {
    "feedback": "dummy content",
    "recommendation": "dummy content",
    "score": 4.5
  }
}

valid_speaking_celery_output = [
  {
    "Fluency & Coherence": {
      "feedback": "dummy content",
      "recommendation": "dummy content",
      "breakdown": [
        {
          "feedback": "dummy content",
          "recommendation": "dummy content",
          "name": "Fluency",
          "score": 5
        },
        {
          "feedback": "dummy content",
          "recommendation": "dummy content",
          "name": "Coherence",
          "score": 6
        }
      ]
    }
  },
  {
    "Lexical Resource": {
      "feedback": "dummy content",
      "recommendation": "dummy content",
      "breakdown": [
        {
          "feedback": "dummy content",
          "recommendation": "dummy content",
          "name": "Range of Vocabulary",
          "score": 4
        },
        {
          "feedback": "dummy content",
          "recommendation": "dummy content",
          "name": "Appropriateness of Vocabulary",
          "score": 5
        },
        {
          "feedback": "dummy content",
          "recommendation": "dummy content",
          "name": "Idiomatic Language",
          "score": 3
        }
      ]
    }
  },
  {
    "Grammatical Range & Accuracy": {
      "feedback": "dummy content",
      "recommendation": "dummy content",
      "breakdown": [
        {
          "feedback": "dummy content",
          "recommendation": "dummy content",
          "name": "Range of Sentence Structures",
          "score": 3
        },
        {
          "feedback": "dummy content",
          "recommendation": "dummy content",
          "name": "Accuracy of Grammar",
          "score": 3
        },
        {
          "feedback": "dummy content",
          "recommendation": "dummy content",
          "name": "Punctuation and Intonation",
          "score": 3
        }
      ]
    }
  },
  {
    "General Feedback": {
      "feedback": "dummy content",
      "recommendation": "dummy content",
      "score": 4.5
    }
  }
]

test_data = [
    ({
        "ready": False,
        "successful": False,
        "failed": False
    }, 202, {"detail": "Pending"}),
    ({
        "ready": True,
        "successful": False,
        "failed": True
    }, 400, {"detail": "Task evaluation failed, try again"}),
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
    with patch('app.main.AsyncResult') as mock_async_result:
        mock_async_result.return_value = group_result_mock(group_result)
        yield mock_async_result


@pytest.mark.parametrize("group_result, status_code, message", test_data)
def test_get_task_result(set_group_result_mock, group_result, status_code, message):
    response = client.get("/tasks/test-task-id")
    assert response.status_code == status_code
    assert json.loads(response.text) == message
