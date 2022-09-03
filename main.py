import logging.config
import json
import os
from typing import Dict

import requests
from dotenv import load_dotenv

from config_log import LOGGER_CONFIG
from exceptions import FileReadingError, TimeZoneFormatError

load_dotenv()

logging.config.dictConfig(LOGGER_CONFIG)
_logger = logging.getLogger('script_logger')


DATE_PERIODS = ('1-5', '6-10', '11-15', '16-20', '21-25', '25-31')
TIMEZONE = os.getenv('TIMEZONE')


def sum_hours(hours: str, hours_tz: str) -> str:
    """Складывает часы в формате 23:00"""
    sum = int(hours) + int(hours_tz)
    if int(hours_tz) > 12:
        _logger.error(f'Временная зона "+{hours_tz}" не верного формата.')
        raise TimeZoneFormatError('Временная зона указана не верно.')
    elif sum > 23:
        sum -= 24
    return str(sum)


def subtracting_hours(hours: str, hours_tz: str) -> str:
    """Вычитает часы в формате 23:00"""
    dif = int(hours) - int(hours_tz)
    if int(hours_tz) > 12:
        _logger.error(f'Временная зона "-{hours_tz}" не верного формата.')
        raise TimeZoneFormatError('Временная зона указана не верно.')
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
        _logger.error(f'Временная зона "{TIMEZONE}" не верного формата.')
        raise TimeZoneFormatError('Временная зона указана не верно.')
    return time


def get_twilight_times() -> Dict[str, str]:
    """Возвращает время начала и окончания сумерок с учетом временной зоны"""
    pass


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
        _logger.error('Не удалось прочитать файл lighting_schedule.json')
        raise FileReadingError('Ошибка чтения файла lighting_schedule.json')
    return lighting_schedule


def write_lighting_schedule(
        month: str, date_period: str, sun_rise_set: Dict[str, str]
) -> None:
    """
    Записывает в расписание восхода и заката солнца новые данные.
    """
    lighting_schedule = read_lighting_schedule()
    if month not in lighting_schedule.keys():
        _logger.debug(f'Месяца {month} не было в графике. Он добавлен в файл')
        lighting_schedule[month] = {}
    lighting_schedule[month][date_period] = sun_rise_set
    with open('data/lighting_schedule.json', 'w', encoding='utf-8') as f:
        json.dump(lighting_schedule, fp=f, indent=4)
    _logger.debug(f'В {month}[{date_period}] добавлено {sun_rise_set}')


def main():
    pass


if __name__ == '__main__':
   print(corrects_time_by_time_zone('21:30'))
