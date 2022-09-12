import json
import time
from collections import namedtuple
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from typing import Dict, Tuple

import requests

from exceptions import (
    FileReadingError, RequestAPISunriseSunsetError,
    ENVError
)
from settings import (
    _logger, TIMEZONE, LATITUDE, LONGITUDE, DATE_PERIODS, RETRY_TIME,
    TIMEOFFSETON, TIMEOFFSETOFF
)
from zont import status_lighting


def format_time(time_for_pars: str, time_zone: str) -> str:
    """
    Форматирует строку времени из вида <4:19:34 PM> в <19:19> (+3)
    с учетом часового пояса
    """
    time_obj = datetime.strptime(time_for_pars, '%I:%M:%S %p')
    utc_zone = timezone(timedelta(hours=0))
    my_zone = timezone(timedelta(hours=int(time_zone)))
    time_obj = time_obj.replace(tzinfo=utc_zone)
    time_obj = time_obj.astimezone(my_zone)
    return time_obj.strftime('%H:%M')


def adds_time_offset(time_in: str, time_offset: str) -> str:
    """Добавляет корректировку времени на заданное число минут"""
    time_obj = datetime.strptime(time_in, '%H:%M')
    delta = timedelta(minutes=int(time_offset))
    return (time_obj + delta).strftime('%H:%M')


def get_times_turn_on_off_light() -> Dict[str, str]:
    """
    Возвращает время включения и отключения освещения
    с учетом временной зоны.
    """
    url = 'https://api.sunrise-sunset.org/json'
    data = {
        'lat': LATITUDE,
        'lng': LONGITUDE,
        'date': datetime.now().date().strftime('%Y-%m-%d')
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

    time_light_on = format_time(twilight_end, TIMEZONE)
    time_light_off = format_time(twilight_begin, TIMEZONE)

    times_turn_on_off_light = {
        'light_on': adds_time_offset(time_light_on, TIMEOFFSETON),
        'light_off': adds_time_offset(time_light_off, TIMEOFFSETOFF)
    }

    return times_turn_on_off_light


def read_lighting_schedule() -> Dict[str, Dict]:
    """
    Считывает расписание (включения и отключения освещения) из файла,
    и возвращает словарь.
    """
    try:
        with open('data/lighting_schedule.json', 'r', encoding='utf-8') as f:
            lighting_schedule = json.load(f)
            _logger.debug('Файл lighting_schedule.json прочитан')
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
        _logger.info(f'Месяца {month} не было в графике. Он добавлен в файл')
        lighting_schedule[month] = {}
    lighting_schedule[month][date_period] = sun_rise_set
    with open('data/lighting_schedule.json', 'w', encoding='utf-8') as f:
        json.dump(lighting_schedule, fp=f, indent=4)
    _logger.info(f'В {month}[{date_period}] добавлено {sun_rise_set}')


def check_env_variable() -> bool:
    """Проверяет доступность переменных окружения."""
    return all([TIMEZONE, LATITUDE, LONGITUDE])


def get_date_period(day: str) -> str:
    """Принимает номер дня месяца и возвращает период дней из графика"""
    for i in range(len(DATE_PERIODS)):
        if int(day) in range(
                DATE_PERIODS[i].starting_date,
                DATE_PERIODS[i].finishing_date + 1
        ):
            date_period = (f'{DATE_PERIODS[i].starting_date}-' 
                           f'{DATE_PERIODS[i].finishing_date}')
            return date_period
    raise ValueError('День должен быть в диапазоне от 1 до 31')


def load_times_turn_on_off_light(
        lighting_schedule: Dict, month: str, period: str) -> Tuple[Dict, Dict]:
    """
    Получает время включения и выключения из файла,
    если данных нет, то подгружает из интернета
    """
    try:
        return lighting_schedule[month][period], lighting_schedule
    except KeyError:
        times_turn_on_off_light = get_times_turn_on_off_light()
        write_lighting_schedule(
            month, period, times_turn_on_off_light
        )
        lighting_schedule = read_lighting_schedule()
        return times_turn_on_off_light, lighting_schedule


def is_time_in_interval(time_checked: str, start_interval_time: str,
                        end_interval_time: str) -> bool:
    """Проверяет вхождение времени в заданный интервал"""
    time_checked_obj = datetime.strptime(time_checked, '%H:%M')
    time_light_on_obj = datetime.strptime(start_interval_time, '%H:%M')
    time_light_off_obj = datetime.strptime(end_interval_time, '%H:%M')
    if time_light_off_obj <= time_checked_obj < time_light_on_obj:
        return False
    return True


def main():
    _logger.warning('STARTED')
    if check_env_variable():
        _logger.info('Переменные окружения загружены')
    else:
        error = 'Переменные окружения недоступны, проверьте файл .env'
        _logger.error(error)
        raise ENVError(error)

    flag_light_on = status_lighting()

    LightingControlTime = namedtuple('LightingControlTime',
                                     'light_on light_off')

    lighting_schedule = read_lighting_schedule()
    date_start = datetime.now()
    _logger.debug(f'{date_start=}')
    month_start = date_start.strftime('%B')
    _logger.debug(f'{month_start=}')
    period_start = get_date_period(date_start.strftime('%d'))
    _logger.debug(f'{period_start=}')
    times_turn_on_off_light, lighting_schedule = load_times_turn_on_off_light(
        lighting_schedule, month_start, period_start
    )
    lighting_control_time = LightingControlTime(
        light_on=times_turn_on_off_light['light_on'],
        light_off=times_turn_on_off_light['light_off']
    )
    _logger.info(f'Время включения и выключения '
                 f'освещения: {times_turn_on_off_light}')

    while True:
        try:
            date_now = datetime.now()
            _logger.debug(f'{date_now=}')
            time_now = date_now.strftime('%H:%M')
            _logger.debug(f'{time_now=}')
            month_now = date_now.strftime('%B')
            _logger.debug(f'{month_now=}')
            period_now = get_date_period(date_now.strftime('%d'))
            _logger.debug(f'{period_now=}')

            if not flag_light_on and is_time_in_interval(
                time_now, *lighting_control_time
            ):
                _logger.warning(f'ОСВЕЩЕНИЕ ВКЛЮЧЕНО!!!!!')
                flag_light_on = True

            if flag_light_on and not is_time_in_interval(
                    time_now, *lighting_control_time
            ):
                _logger.warning(f'ОСВЕЩЕНИЕ ВЫКЛЮЧЕНО!!!!!')
                flag_light_on = False

            if period_start != period_now:
                (
                    times_turn_on_off_light, lighting_schedule
                 ) = load_times_turn_on_off_light(
                    lighting_schedule, month_now, period_now
                )
                period_start = period_now
                lighting_control_time = LightingControlTime(
                    light_on=times_turn_on_off_light['light_on'],
                    light_off=times_turn_on_off_light['light_off']
                )
                _logger.debug(f'{period_start=}')
                _logger.info(f'Время включения и выключения '
                             f'освещения: {times_turn_on_off_light}')

        except RequestAPISunriseSunsetError:
            _logger.error(f'Ошибка запроса к API.')

        except FileReadingError:
            _logger.error('Не удалось прочитать файл lighting_schedule.json')

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            _logger.error(message)

        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
