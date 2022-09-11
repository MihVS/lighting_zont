import logging.config
import os

from dotenv import load_dotenv

from config_log import LOGGER_CONFIG

load_dotenv()

logging.config.dictConfig(LOGGER_CONFIG)
_logger = logging.getLogger('script_logger')


RETRY_TIME = 60

DATE_PERIODS = ('1-5', '6-10', '11-15', '16-20', '21-25', '25-31')
TIMEZONE = os.getenv('TIMEZONE')
TIMEOFFSETON = os.getenv('TIMEOFFSETON')
TIMEOFFSETOFF = os.getenv('TIMEOFFSETOFF')
LATITUDE = os.getenv('LATITUDE')
LONGITUDE = os.getenv('LONGITUDE')

CONTENTTYPE = 'application/json'

XZONTTOKEN = os.getenv('XZONTTOKEN')
XZONTCLIENT = os.getenv('XZONTCLIENT')
