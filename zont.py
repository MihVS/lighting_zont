from http import HTTPStatus

import requests

from exceptions import RequestAPIZONTError, ResponseAPIZONTError
from settings import (
    XZONTCLIENT, XZONTTOKEN, CONTENTTYPE, DEVICEID, OBJECTID, _logger
)

HEADERS = {
        'X-ZONT-Token': XZONTTOKEN,
        'X-ZONT-Client': XZONTCLIENT,
        'Content-Type': CONTENTTYPE
    }


def _check_response(response) -> None:
    """Проверяет ответ на ошибки записывает в лог и вызывает исключения"""
    status_code = response.status_code
    _logger.debug(f'Код запроса к API zont: {status_code}')

    if status_code != HTTPStatus.OK:
        error_from_json = response.json()['error_ui']
        _logger.error(f'API zont: {error_from_json}')
        raise RequestAPIZONTError(f'Код запроса {status_code}, '
                                  f'ошибка: {error_from_json}')


def switch_lighting(command: int) -> None:
    """Включает и выключает освещение"""

    url = 'https://zont-online.ru/api/send_z3k_command'
    body = {
        'device_id': DEVICEID,
        'command_name': 'ChangeWebElementState',
        'command_args': {
            'state': command
        },
        'object_id': OBJECTID,
        'is_guaranteed': True
    }

    response = requests.post(url=url, json=body, headers=HEADERS)

    _check_response(response)


def status_lighting():
    """Проверяет статус освещения True - вкл, False - выкл"""

    url = 'https://zont-online.ru/api/devices'
    body = {'load_io': True}

    response = requests.post(url=url, json=body, headers=HEADERS)

    _check_response(response)
    try:
        statuses_all = response.json()['devices'][0]['io']['z3k-state']
        status = statuses_all[str(OBJECTID)]['state']
        _logger.debug(f'Статус состояния выхода контроллера: {status}')
    except (KeyError, IndexError):
        raise ResponseAPIZONTError('Проверьте ответ от сервера zont')

    return bool(status)
