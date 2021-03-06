import json
import logging
import os
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
        auth=("api", os.environ.get("MAILGUN_KEY", "")),
        data={
                "from": "MatchDay <mailgun@sandbox415bef09bf94429cbe10a8f6dd874063.mailgun.org>",
                "to": to,
                "subject": "Matchday Error",
                "text": body
             }
        )


def get_pulse_response(url):
    headers = {
        'authority': 'footballapi.pulselive.com',
        'origin': 'https://www.premierleague.com',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'accept': '*/*',
        'sec-fetch-site': 'cross-site',
        'sec-fetch-mode': 'cors',
        'referer': 'https://footballapi.pulselive.com/',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8'
    }

    resp = requests.request("GET", url, headers=headers)
    return json.loads(resp.content)


def calculate_proper_duration(duration):
    '''
    when a user makes a picks for 60 mins at minute 50, the pick actually plays
    only for 40 minutes and not the mentioned 60. This function is to calculate
    the actual amount of time he plays
    '''
    if duration < 30:
        return 15
    elif duration < 60:
        return 30
    else:
        return 60