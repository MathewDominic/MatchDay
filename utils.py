import os
import logging
from logging.handlers import RotatingFileHandler

def initLogging(LOG_LEVEL, filename=None, logger_name=""):
    if filename is not None:
        filename = filename
    logging.basicConfig(
        level=LOG_LEVEL,
        format='[%(asctime)s] p%(process)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',
    )
    logFormatter = logging.Formatter('[%(asctime)s] p%(process)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s')

    rootLogger = logging.getLogger(logger_name)
    rootLogger.setLevel(LOG_LEVEL)
    print "init logging: level: %s, file: %s" % (logging.getLevelName(LOG_LEVEL), filename)

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
