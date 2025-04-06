class TokenMissingError(Exception):
    """Исключение, вызываемое при отсутствии переменных окружения."""


class APIRequestError(Exception):
    """Ошибка при запросе к API Практикума."""


class APIResponseFormatError(Exception):
    """Ответ от API не соответствует ожидаемому формату."""


class StatusUnknownError(Exception):
    """Неизвестный статус домашней работы."""
