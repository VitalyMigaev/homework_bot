class EndpointNotAvailable(Exception):
    """Исключение, возникающее, когда конечная точка недоступна."""


class UnexpectedHomeworkStatus(Exception):
    """Исключение, возникающее при неожиданном статусе домашнего задания."""


class HomeworkNameNotFound(Exception):
    """Исключение, возникающее, когда имя домашнего задания не найдено."""


class HomeworkNotFound(Exception):
    """Исключение, возникающее, когда домашнее задание не найдено."""


class StatusNotFound(Exception):
    """Исключение, возникающее, когда статус не найден."""


class TokenError(Exception):
    """Кастомное исключение для ошибок токенов."""

    def __init__(self, missing_tokens):
        self.missing_tokens = missing_tokens
        missing_tokens_str = ', '.join(missing_tokens)
        super().__init__(
            "Отсутствуют обязательные переменные окружения: "
            + missing_tokens_str
        )
