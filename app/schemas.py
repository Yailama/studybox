from typing import Literal, Union, Dict, Any, List
from pydantic import BaseModel, UUID4, model_validator, Field


class AnswerBase(BaseModel):
    question: str
    answer: str


class WritingAnswer(AnswerBase):
    question_type: Literal["writing"]
    question_part: Literal["1", "2"]


# class SpeakingAnswer(AnswerBase):
#     question_type: Literal["speaking"]
#     question_part: Literal["1", "2", "3"]


class AnswerIn(BaseModel):
    task: WritingAnswer


class TaskRegistration(BaseModel):
    task_id: UUID4


class BandScores(BaseModel):
    name: Literal[
        "Task Achievement",
        "Coherence & Cohesion",
        "Lexical Resource",
        "Grammatical Range & Accuracy",
        "Fluency & Coherence",
        "Overall Impression"
    ]
    band_breakdown: Dict[str, Dict[str, str]]

    # @model_validator(mode='before')
    # @classmethod
    # def check_keys(cls, data: Any) -> Any:
    #     if isinstance(data, dict):
    #         keys_to_check = {str(i) for i in range(10)}
    #         keys = set(data["scores"].keys())
    #
    #         assert keys_to_check == keys, f'Expected {keys_to_check}, got {keys}'
    #
    #     return data


class WritingBandDescriptors(BaseModel):
    descriptors: List[BandScores]

    @model_validator(mode='before')
    @classmethod
    def check_keys(cls, data: Any) -> Any:
        if isinstance(data, dict):
            keys_to_check = {"Task Achievement",
                             "Coherence & Cohesion",
                             "Lexical Resource",
                             "Grammatical Range & Accuracy",
                             }
            keys = {x['name'] for x in data['descriptors']}
            assert keys_to_check == keys, f'Expected exactly Writing Band Descriptors: ' \
                                          f'{keys_to_check}, got {keys}'

        return data


class SpeakingBandDescriptors(BaseModel):
    descriptors: List[BandScores]

    @model_validator(mode='before')
    @classmethod
    def check_keys(cls, data: Any) -> Any:
        if isinstance(data, dict):
            keys_to_check = {"Fluency & Coherence", "Lexical Resource",
                             "Grammatical Range & Accuracy"}
            keys = {x['name'] for x in data['descriptors']}
            assert keys_to_check == keys, f'Expected exactly Speaking Band Descriptors: ' \
                                          f'{keys_to_check}, got {keys}'

        return data


class PartBandDescriptors(BaseModel):
    parts: Dict[str, SpeakingBandDescriptors | WritingBandDescriptors]


class BandDescriptors(BaseModel):
    sections: Dict[Literal["writing", "speaking"], PartBandDescriptors]

    @model_validator(mode='before')
    @classmethod
    def check_keys(cls, data: Any) -> Any:
        if isinstance(data, dict):
            sections = set(data["sections"].keys())
            assert sections == {"writing", "speaking"}, f"Expected sections: writing, " \
                                                        f"speaking, got {sections}"

            writing_parts = set(data["sections"]["writing"]["parts"].keys())
            speaking_parts = set(data["sections"]["speaking"]["parts"].keys())

            assert writing_parts == {"1", "2"}, f"Expected parts: 1, 2 got {writing_parts}"
            assert speaking_parts == {"1"}, f"Expected parts: 1 got {speaking_parts}. " \
                                            f"All speaking parts use sane band descriptor"

        return data

    @model_validator(mode='after')
    @classmethod
    def extrapolate_speaking(cls, data: Any) -> Any:
        data.sections["speaking"].parts["2"] = data.sections["speaking"].parts["1"]
        data.sections["speaking"].parts["3"] = data.sections["speaking"].parts["1"]
        return data


class Feedback(BaseModel):
    feedback: str
    recommendation: str

class WritingGeneralFeedback(Feedback):
    rewriting: str

class WritingGeneralFeedbackOut(WritingGeneralFeedback):
    score: float

class SpeakingGeneralFeedbackOut(Feedback):
    score: float

class BandDescriptorBreakdown(Feedback):
    name: str
    score: int
    feedback: str
    recommendation: str | None

class BandDescriptorFeedback(Feedback):
    feedback: str
    recommendation: str
    breakdown: List[BandDescriptorBreakdown]

class WritingFeedbackOut(BaseModel):
    task_achievement: BandDescriptorFeedback = Field(alias="Task Achievement")
    coherence_and_cohesion: BandDescriptorFeedback = Field(alias="Coherence & Cohesion")
    lexical_resource: BandDescriptorFeedback = Field(alias="Lexical Resource")
    grammar: BandDescriptorFeedback = Field(alias="Grammatical Range & Accuracy")
    general: WritingGeneralFeedbackOut = Field(alias="General Feedback")


class SpeakingFeedbackOut(BaseModel):
    fluency_and_cohesion: BandDescriptorFeedback = Field(alias="Fluency & Coherence")
    lexical_resource: BandDescriptorFeedback = Field(alias="Lexical Resource")
    grammar: BandDescriptorFeedback = Field(alias="Grammatical Range & Accuracy")
    general: SpeakingGeneralFeedbackOut = Field(alias="General Feedback")

    class Config:
        allow_population_by_field_name = True
