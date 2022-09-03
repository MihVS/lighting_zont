from datetime import datetime
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

# Все вот это до функций я бы выкинул в отдельный модуль. 
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

# вот до сюда

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
    arithmetic_symbol = TIMEZONE[0]  #нечитаемо тут и везде. ЧТо она значит? Используй свой класс, Enum или NamedTuple
    time_list = time_utc.split(':')
    if arithmetic_symbol == '+':  # Всю эту мешанину условий можно завернуть в класс и использовать gettattr
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

    # Уверен, что все это дело умеет делать какой-нибудь datetime.datetime.strptime. 
    # Можно сильно проще, а главное оно уже покрыто тестами

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


    # А! Я понял! Что за функции сверху :) Это из UTC в нужный часовой пояс? 
    # Уверен, что в datetime найдется нужный инсрумент, чем самописаные функции

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

    # Если это домашний код, то сойдет. Если пойдет в продакшн, 
    # то нужно еще ченуть json на корректность потом


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


def get_date_period(date: str) -> str:
    """Принимает номер дня месяца и возвращает период дней из графика"""
    date = int(date)
    for date_period in DATE_PERIODS:
        period = date_period.split('-')

        # В условии напрашивается использование более читаемой структуры данных, 
        # типа своего класса, NamedTuple (или его наследника). 
        if date in [d for d in range(int(period[0]), int(period[1]) + 1)]:  # if date in range(int(period[0]), int(period[1]) + 1):... Но я бы подумал над изменением DATE_PERIODS. И эта функция вся изменится тогда
            return date_period


def check_time_in_lighting_schedule(
        lighting_schedule: Dict, month: str, date_period: str) -> bool:
    """
    Проверяет есть ли данные о включении и выключении освещения
    в нужный период
    """
    try:
        return bool(lighting_schedule[month][date_period])
    except KeyError:
        return False


def main():
    if check_env_variable():
        _logger.debug('Переменные окружения доступны')
    else:
        error = 'Переменные окружения недоступны, проверьте файл .env'
        _logger.error(error)
        raise ENVError(error)

    time_zero_obj = datetime.strptime('00:00', '%H:%M')
    time_max_obj = datetime.strptime('23:59', '%H:%M')
    flag_light_on = False

    lighting_schedule = read_lighting_schedule()
    date_start = datetime.now()
    _logger.info(f'{date_start=}')
    month_start = date_start.strftime('%B')
    _logger.info(f'{month_start=}')
    period_start = get_date_period(date_start.strftime('%d'))
    _logger.info(f'{period_start=}')

    # это точно должна быть отдельная функция

    if not check_time_in_lighting_schedule(
            lighting_schedule, month_start, period_start
    ):
        times_turn_on_off_light = get_times_turn_on_off_light()
        write_lighting_schedule(
            month_start, period_start, times_turn_on_off_light
        )
        lighting_schedule = read_lighting_schedule()
    else:
        times_turn_on_off_light = lighting_schedule[month_start][period_start]

    _logger.info(f'Время включения и выключения '
                 f'освешения: {times_turn_on_off_light}')
    # print(get_date_period('25'))
    # print(check_time_in_lighting_schedule(lighting_schedule, 'January', '6-10'))

    while True:
        try:
            date_now = datetime.now()
            _logger.info(f'{date_now=}')
            time_now = date_now.strftime('%H:%M')
            _logger.info(f'{time_now=}')
            month_now = date_now.strftime('%B')
            _logger.info(f'{month_now=}')
            period_now = get_date_period(date_now.strftime('%d'))
            _logger.info(f'{period_now=}')

            if period_start != period_now:
                if not check_time_in_lighting_schedule(
                        lighting_schedule, month_now, period_now
                ):
                    times_turn_on_off_light = get_times_turn_on_off_light()
                    write_lighting_schedule(
                        month_now, period_now, times_turn_on_off_light
                    )
                    lighting_schedule = read_lighting_schedule()
                else:
                    times_turn_on_off_light = lighting_schedule[month_start][
                        period_start]
                _logger.info(f'Время включения и выключения '
                             f'освешения: {times_turn_on_off_light}')

            time_now_obj = datetime.strptime(time_now, '%H:%M')
            time_light_on_obj = datetime.strptime(
                times_turn_on_off_light['light_on'], '%H:%M'
            )
            time_light_off_obj = datetime.strptime(
                times_turn_on_off_light['light_off'], '%H:%M'
            )

            # Вот эти условия жирные надо убрать в функцию is_time_in_interval(time, start_interval_time, end_interval_time) и чекать.
            # Плюс у питона есть ленивые вычисления и проверка на флаг, кмк, приоритетнее. Я бы ее сунул первой, а не последней.
            # А то тут аж мозг напрягся, что происходит :)
            # Плюс тоже убрал бы в отдельную функцию. Main стоид разгрузить. В вызывающем коде сидит куча логики приложения. 

            if ((time_max_obj >= time_now_obj >= time_light_on_obj) or (
                time_zero_obj <= time_now_obj < time_light_off_obj)) and (
                    not flag_light_on):
                _logger.debug(f'ОСВЕЩЕНИЕ ВКЛЮЧЕНО!!!!!')
                flag_light_on = True

            # if :
            #     _logger.debug(f'ОСВЕЩЕНИЕ ВЫКЛЮЧЕНО!!!!!')

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
    main()
