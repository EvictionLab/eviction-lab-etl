import logging

# Provides a simple logger for logging to the console and/or file
def create_logger(name, console_lvl='DEBUG', file_lvl=None):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # create file handler which logs even debug messages
    if file_lvl:
      fh = logging.FileHandler('log/'+name+'.txt')
      fh.setLevel(getattr(logging, file_lvl))
      fh.setFormatter(formatter)
      logger.addHandler(fh)

    # create console handler with a higher log level
    if console_lvl:
      ch = logging.StreamHandler()
      ch.setLevel(getattr(logging, console_lvl))
      ch.setFormatter(formatter)
      logger.addHandler(ch)

    return logger

# create a logger for the process
logger = create_logger('build_log', console_lvl='DEBUG', file_lvl='WARN')