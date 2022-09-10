class FileReadingError(Exception):
    """Ошибка чтения файла"""
    pass


class RequestAPISunriseSunsetError(Exception):
    """Ошибка запроса к сервису api.sunrise-sunset.org/json"""
    pass


class ENVError(Exception):
    """Ошибка доступности переменных окружения"""
    pass
