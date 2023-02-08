class FileReadingError(Exception):
    """Ошибка чтения файла"""
    pass


class RequestAPISunriseSunsetError(Exception):
    """Ошибка запроса к сервису api.sunrise-sunset.org/json"""
    pass


class RequestAPIZONTError(Exception):
    """Ошибка запроса к сервису zont-online.ru/api"""
    pass


class ResponseAPIZONTError(Exception):
    """Ответ от API zont в неправильном варианте"""
    pass


class ENVError(Exception):
    """Ошибка доступности переменных окружения"""
    pass
