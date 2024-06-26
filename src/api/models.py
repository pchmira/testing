"""
Модуль Pydantic моделей, для описания запросов и ответов к API.
"""
from pydantic import BaseModel


# Класс, описывающий типы полей в объекте, который типизирован этим классом.
class Question(BaseModel):
    """
    Класс валидации данных вопроса.
    """
    question: str
    answer_1: str
    answer_2: str
    answer_3: str
    answer_4: str
    correct_answer: str


# Класс, описывающий типы полей в объекте, который типизирован этим классом.
class Test(BaseModel):
    """
    Класс валидации данных запроса при создании/отправлении теста.
    """
    test_name: str
    quest_1: Question
    quest_2: Question
    quest_3: Question
    quest_4: Question
    quest_5: Question
    quest_6: Question
    quest_7: Question
    quest_8: Question
    quest_9: Question
    quest_10: Question
