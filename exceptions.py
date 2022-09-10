class FileReadingError(Exception):
    """Ошибка чтения файла"""
    pass


class TimeZoneFormatError(Exception):
    """Не верный формат временной зоны"""
    pass


class RequestAPISunriseSunsetError(Exception):
    """Ошибка запроса к сервису api.sunrise-sunset.org/json"""
    pass


class ValueHoursError(Exception):
    """Не верное значение часов"""
    pass


class ENVError(Exception):
    """Ошибка доступности переменных окружения"""
    pass
