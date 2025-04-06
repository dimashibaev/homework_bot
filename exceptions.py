class TokenMissingError(Exception):
    """Исключение, вызываемое при отсутствии переменных окружения."""
    pass


class APIRequestError(Exception):
    """Ошибка при запросе к API Практикума."""
    pass


class APIResponseFormatError(Exception):
    """Ответ от API не соответствует ожидаемому формату."""
    pass


class StatusUnknownError(Exception):
    """Неизвестный статус домашней работы."""
    pass
