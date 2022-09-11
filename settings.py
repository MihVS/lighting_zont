import logging.config
import os

from dotenv import load_dotenv
from collections import namedtuple

from config_log import LOGGER_CONFIG

load_dotenv()

logging.config.dictConfig(LOGGER_CONFIG)
_logger = logging.getLogger('script_logger')


RETRY_TIME = 60

DatePeriods = namedtuple('DatePeriods', 'starting_date finishing_date')
DATE_PERIODS = (
    DatePeriods(starting_date=1, finishing_date=5),
    DatePeriods(starting_date=5, finishing_date=10),
    DatePeriods(starting_date=11, finishing_date=15),
    DatePeriods(starting_date=16, finishing_date=20),
    DatePeriods(starting_date=21, finishing_date=25),
    DatePeriods(starting_date=26, finishing_date=31),
)
TIMEZONE = os.getenv('TIMEZONE')
TIMEOFFSETON = os.getenv('TIMEOFFSETON')
TIMEOFFSETOFF = os.getenv('TIMEOFFSETOFF')
LATITUDE = os.getenv('LATITUDE')
LONGITUDE = os.getenv('LONGITUDE')

CONTENTTYPE = 'application/json'

XZONTTOKEN = os.getenv('XZONTTOKEN')
XZONTCLIENT = os.getenv('XZONTCLIENT')
