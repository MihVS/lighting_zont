import json
import logging.config
import os
import time
from http import HTTPStatus
from typing import Dict

import requests
from dotenv import load_dotenv

from config_log import LOGGER_CONFIG
from exceptions import (
    FileReadingError, TimeZoneFormatError, RequestAPISunriseSunsetError,
    ValueHoursError, ENVError
)

load_dotenv()

logging.config.dictConfig(LOGGER_CONFIG)
_logger = logging.getLogger('script_logger')


RETRY_TIME = 60
DATE_PERIODS = ('1-5', '6-10', '11-15', '16-20', '21-25', '25-31')
CONTENTTYPE = 'application/json'
XZONTTOKEN = os.getenv('XZONTTOKEN')
XZONTCLIENT = os.getenv('XZONTCLIENT')
TIMEZONE = os.getenv('TIMEZONE')
LATITUDE = os.getenv('LATITUDE')
LONGITUDE = os.getenv('LONGITUDE')


def sum_hours(hours: str, hours_sum: str) -> str:
    """Складывает часы в формате 23:00"""
    sum = int(hours) + int(hours_sum)
    if int(hours_sum) > 12:
        raise ValueHoursError('Не верное значение складываемых часов')
    if 47 > sum > 23:
        sum -= 24
    return str(sum)


def subtracting_hours(hours: str, hours_tz: str) -> str:
    """Вычитает часы в формате 23:00"""
    dif = int(hours) - int(hours_tz)
    if int(hours_tz) > 12:
        raise ValueHoursError('Не верное значение вычетаемых часов')
    elif dif < 0:
        dif += 24
    return str(dif)


def corrects_time_by_time_zone(time_utc: str) -> str:
    """Корректирует время по заданной временной зоне"""
    arithmetic_symbol = TIMEZONE[0]
    time_list = time_utc.split(':')
    if arithmetic_symbol == '+':
        time = ':'.join(
            [sum_hours(time_list[0], TIMEZONE[1:]), time_list[1]]
        )
    elif arithmetic_symbol == '-':
        time = ':'.join(
            [subtracting_hours(time_list[0], TIMEZONE[1:]), time_list[1]]
        )
    else:
        raise TimeZoneFormatError('Временная зона указана не верно.')
    return time


def format_time(time: str) -> str:
    """Форматирует строку времени из вида <4:19:34 PM> в <16:19>"""
    time_value, pm_am = time.split()
    _logger.debug(f'{time_value=}, {pm_am=}')
    hours, minutes, seconds = time_value.split(':')
    if pm_am == 'PM':
        hours = sum_hours(hours, '12')
    return ':'.join([hours, minutes])


def get_times_turn_on_off_light() -> Dict[str, str]:
    """
    Возвращает время включения и отключения освещения
    с учетом временной зоны.
    """
    url = 'https://api.sunrise-sunset.org/json'
    data = {
        'lat': LATITUDE,
        'lng': LONGITUDE
    }

    response = requests.get(url, data)
    status_code = response.status_code
    _logger.debug(f'Код запроса к эндпоинту API: {status_code}')

    if status_code != HTTPStatus.OK:
        raise RequestAPISunriseSunsetError(f'Код запроса {status_code}')

    status_from_json = response.json()['status']
    _logger.debug(f'Статус код из JSON ответа: {status_from_json}')

    if status_from_json != 'OK':
        raise RequestAPISunriseSunsetError(f'Статус в теле ответа '
                                           f'{status_from_json}')

    twilight_begin = response.json()['results']['civil_twilight_begin']
    twilight_end = response.json()['results']['civil_twilight_end']
    _logger.debug(f'{twilight_begin=}, {twilight_end=}')

    time_light_on = corrects_time_by_time_zone(format_time(twilight_end))
    time_light_off = corrects_time_by_time_zone(format_time(twilight_begin))

    times_turn_on_off_light = {
        'light_on': time_light_on,
        'light_off': time_light_off
    }

    return times_turn_on_off_light


def read_lighting_schedule() -> Dict[str, Dict]:
    """
    Считывает расписание восхода и заката солнца из файла,
    и возвращает словарь.
    """
    try:
        with open('data/lighting_schedule.json', 'r', encoding='utf-8') as f:
            lighting_schedule = json.load(f)
            _logger.info('Файл lighting_schedule.json прочитан')
    except Exception:
        raise FileReadingError('Ошибка чтения файла lighting_schedule.json')
    return lighting_schedule


def write_lighting_schedule(
        month: str, date_period: str, sun_rise_set: Dict[str, str]
) -> None:
    """
    Записывает в расписание (включения и отключения освещения) новые данные.
    """
    lighting_schedule = read_lighting_schedule()
    if month not in lighting_schedule.keys():
        _logger.debug(f'Месяца {month} не было в графике. Он добавлен в файл')
        lighting_schedule[month] = {}
    lighting_schedule[month][date_period] = sun_rise_set
    with open('data/lighting_schedule.json', 'w', encoding='utf-8') as f:
        json.dump(lighting_schedule, fp=f, indent=4)
    _logger.debug(f'В {month}[{date_period}] добавлено {sun_rise_set}')


def check_env_variable() -> bool:
    """Проверяет доступность переменных окружения."""
    return all([XZONTTOKEN, XZONTCLIENT, TIMEZONE, LATITUDE, LONGITUDE])


def main():
    if check_env_variable():
        _logger.debug('Переменные окружения доступны')
    else:
        error = 'Переменные окружения недоступны, проверьте файл .env'
        _logger.error(error)
        raise ENVError(error)

    while True:
        try:
            pass

        except ValueHoursError:
            _logger.error(f'Прибавляемые(Вычитаемые) часы должны '
                          f'быть не больше(меньше) 12(-12)')

        except RequestAPISunriseSunsetError:
            _logger.error(f'Ошибка запроса к API.')

        except TimeZoneFormatError:
            _logger.error(f'Временная зона "{TIMEZONE}" не верного формата.')

        except FileReadingError:
            _logger.error('Не удалось прочитать файл lighting_schedule.json')

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            _logger.error(message)

        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    print(get_times_turn_on_off_light())
