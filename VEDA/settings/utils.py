"""
Common utils for settings.
"""
import os
import platform
import sys
from logging.handlers import SysLogHandler


def get_logger_config(log_dir='/var/tmp',
                      logging_env="no_env",
                      edx_filename="edx.log",
                      dev_env=False,
                      debug=False,
                      local_loglevel='INFO',
                      service_variant='video-pipeline'):
    """
    Return the appropriate logging config dictionary. You should assign the
    result of this to the LOGGING var in your settings.

    If dev_env is set to true logging will not be done via local rsyslogd,
    instead, application logs will be dropped in log_dir.

    "edx_filename" is ignored unless dev_env is set to true since otherwise logging is handled by rsyslogd.
    """

    # Revert to INFO if an invalid string is passed in
    if local_loglevel not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
        local_loglevel = 'INFO'

    console_loglevel = 'DEBUG' if debug else 'INFO'

    hostname = platform.node().split(".")[0]
    syslog_format = (
        "[service_variant={service_variant}]"
        "[%(name)s][env:{logging_env}] %(levelname)s "
        "[{hostname}  %(process)d] [%(filename)s:%(lineno)d] "
        "- %(message)s"
    ).format(
        service_variant=service_variant,
        logging_env=logging_env, hostname=hostname
    )

    handlers = ['console', 'local']

    logger_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s %(levelname)s %(process)d '
                          '[%(name)s] %(filename)s:%(lineno)d - %(message)s',
            },
            'syslog_format': {'format': syslog_format},
            'raw': {'format': '%(message)s'},
        },
        'filters': {
            'require_debug_false': {
                '()': 'django.utils.log.RequireDebugFalse'
            }
        },
        'handlers': {
            'console': {
                'level': console_loglevel,
                'class': 'logging.StreamHandler',
                'formatter': 'standard',
                'stream': sys.stdout,
            },
            'mail_admins': {
                'level': 'ERROR',
                'filters': ['require_debug_false'],
                'class': 'django.utils.log.AdminEmailHandler'
            }
        },
        'loggers': {
            'django': {
                'handlers': handlers,
                'propagate': True,
                'level': 'INFO'
            },
            'requests': {
                'handlers': handlers,
                'propagate': True,
                'level': 'WARNING'
            },
            'factory': {
                'handlers': handlers,
                'propagate': True,
                'level': 'WARNING'
            },
            'django.request': {
                'handlers': handlers + [] if debug else ['mail_admins'],
                'propagate': True,
                'level': 'WARNING'
            },
            '': {
                'handlers': handlers,
                'level': 'DEBUG',
                'propagate': False
            },
        }
    }

    if dev_env:
        edx_file_loc = os.path.join(log_dir, edx_filename)
        logger_config['handlers'].update({
            'local': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': local_loglevel,
                'formatter': 'standard',
                'filename': edx_file_loc,
                'maxBytes': 1024 * 1024 * 2,
                'backupCount': 5,
            },
        })
    else:
        logger_config['handlers'].update({
            'local': {
                'level': local_loglevel,
                'class': 'logging.handlers.SysLogHandler',
                # Use a different address for Mac OS X
                'address': '/var/run/syslog' if sys.platform == "darwin" else '/dev/log',
                'formatter': 'syslog_format',
                'facility': SysLogHandler.LOG_LOCAL0,
            },
        })

    return logger_config
