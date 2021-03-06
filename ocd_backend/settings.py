import os
import pickle

from kombu.serialization import register

register('ocd_serializer', pickle.dumps, pickle.loads,
         content_encoding='binary',
         content_type='application/x-pickle2')

REDIS_HOST = "redis"
REDIS_PORT = "6379"

CELERY_CONFIG = {
    'BROKER_URL': 'redis://%s:%s/0' % (REDIS_HOST, REDIS_PORT),
    'CELERY_ACCEPT_CONTENT': ['ocd_serializer'],
    'CELERY_TASK_SERIALIZER': 'ocd_serializer',
    'CELERY_RESULT_SERIALIZER': 'ocd_serializer',
    'CELERY_RESULT_BACKEND': 'ocd_backend.result_backends:OCDRedisBackend+redis://redis:6379/0',
    'CELERY_IGNORE_RESULT': False,
    'CELERY_MESSAGE_COMPRESSION': 'gzip',
    'CELERYD_HIJACK_ROOT_LOGGER': False,
    'CELERY_DISABLE_RATE_LIMITS': True,
    # ACKS_LATE prevents two tasks triggered at the same time to hang
    # https://wiredcraft.com/blog/3-gotchas-for-celery/
    'CELERY_ACKS_LATE': True,
    'WORKER_PREFETCH_MULTIPLIER': 1,
    # Expire results after 30 minutes; otherwise Redis will keep
    # claiming memory for a day
    'CELERY_TASK_RESULT_EXPIRES': 1800,
    'CELERY_REDIRECT_STDOUTS_LEVEL': 'INFO'
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'console': {
            'format': '[%(levelname)s] - %(message)s'
        },
        'file': {
            'format': '[%(asctime)s] [%(name)s] [%(levelname)s] - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        }
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'console'
        },
        'log': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'formatter': 'file',
            'filename': 'log/backend.log'
        }
    },
    'loggers': {
        'ocd_backend': {
            'handlers': ['console', 'log'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'celery': {
            'handlers': ['console', 'log'],
            'level': 'DEBUG',
            'propagate': False,
        }
    }
}

if os.path.exists('/var/log/backend.err'):
    LOGGING['handlers']['docker'] = {
        'level': 'WARN',
        'class': 'logging.FileHandler',
        'formatter': 'file',
        'filename': '/var/log/backend.err'
    }

    LOGGING['loggers']['ocd_backend']['handlers'] = ['console', 'log', 'docker']
    LOGGING['loggers']['celery']['handlers'] = ['console', 'log', 'docker']


ELASTICSEARCH_HOST = 'localhost'
ELASTICSEARCH_PORT = 9200

ROOT_PATH = os.path.dirname(os.path.abspath(__file__))

# The path of the directory used to store temporary files
TEMP_DIR_PATH = os.path.join(ROOT_PATH, 'temp')

# The path of the directory used to store static files
DATA_DIR_PATH = os.path.join(ROOT_PATH, '../data')

# The path of the JSON file containing the sources config
SOURCES_CONFIG_FILE = os.path.join(ROOT_PATH, 'sources/*')

# The name of the index containing documents from all sources
COMBINED_INDEX = 'ori_combined_index'

# The default prefix used for all data
DEFAULT_INDEX_PREFIX = 'ori'

RESOLVER_BASE_URL = 'http://localhost:5000/v0/resolve'
RESOLVER_URL_INDEX = 'ori_resolver'

# The User-Agent that is used when retrieving data from external sources
USER_AGENT = 'Open Raadsinformatie/0.1 (+http://www.openraadsinformatie.nl/)'

# URL where of the API instance that should be used for management commands
# Should include API version and a trailing slash.
# Can be overridden in the CLI when required, for instance when the user wants
# to download dumps from another API instance than the one hosted by OpenState
API_URL = 'http://frontend:5000/v0/'

# The endpoint for the iBabs API
IBABS_WSDL = u'https://www.mijnbabs.nl/iBabsWCFService/Public.svc?singleWsdl'

# The endpoint for the CompanyWebcast API
CWC_WSDL = u'https://services.companywebcast.com/meta/1.2/metaservice.svc?singleWsdl'

# define the location of pdftotext
PDF_TO_TEXT = u'pdftotext'
PDF_MAX_MEDIABOX_PIXELS = 5000000

# Allow any settings to be defined in local_settings.py which should be
# ignored in your version control system allowing for settings to be
# defined per machine.
try:
    from local_settings import *
except ImportError:
    pass
