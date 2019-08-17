import os
import logging
import requests
from logging.handlers import RotatingFileHandler

def init_logging(LOG_LEVEL, filename=None, logger_name=""):
    if filename is not None:
        filename = filename
    logging.basicConfig(
        level=LOG_LEVEL,
        format='[%(asctime)s] p%(process)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',
    )
    logFormatter = logging.Formatter('[%(asctime)s] p%(process)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s')

    rootLogger = logging.getLogger(logger_name)
    rootLogger.setLevel(LOG_LEVEL)
    print(f"init logging: level: {logging.getLevelName(LOG_LEVEL)}, file: {filename}")

    if filename is not None:
        home_path = os.path.expanduser('~')
        dir = os.path.join(home_path, "logs")
        filepath = os.path.join(dir, filename)
        dirs = os.path.dirname(filepath)
        if not os.path.exists(dirs):
            try:
                os.makedirs(dirs)
            except OSError as e:
                raise e
        if logger_name == "" or (not rootLogger.handlers):
            fileHandler = RotatingFileHandler(filepath, maxBytes=5000000, backupCount=5)
            fileHandler.setFormatter(logFormatter)
            fileHandler.setLevel(LOG_LEVEL)
            rootLogger.addHandler(fileHandler)

        return rootLogger
        # os.chmod(filepath, 0o766)


def to_ascii(unicode_str):
    if unicode_str is None:
        return 'None'
    return unicode_str.encode('ascii', 'ignore')


def send_error_mail(to, body):
    return requests.post(
        "https://api.mailgun.net/v3/sandbox415bef09bf94429cbe10a8f6dd874063.mailgun.org/messages",
        auth=("api", "key-f30b6a39a150194f19f93d2ffb997c1b"),
        data={"from": "MatchDay <mailgun@sandbox415bef09bf94429cbe10a8f6dd874063.mailgun.org>",
              "to": to,
              "subject": "Matchday Error",
              "text": body})
