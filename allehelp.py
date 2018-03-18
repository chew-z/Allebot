import logging
from flask_assistant import logger
import os


def isAppEngine():
    server = os.getenv('SERVER_SOFTWARE', '')
    if server is not None and server.startswith('Google App Engine/'): 
        return True 
    else: 
        return False

ISAPPENGINE = isAppEngine()

def _info(msg):
    if ISAPPENGINE:
        logger.info(msg)
    else:
        logging.info(msg)


def _debug(msg):
    if ISAPPENGINE:
        logger.debug(msg)
    else:
        logging.debug(msg)


def _error(msg):
    if ISAPPENGINE:
        logger.info(msg)
    else:
        logging.info(msg)


def use_logging_handler():
    # Imports the Google Cloud client library
    import google.cloud.logging
    # Instantiates a client
    client = google.cloud.logging.Client()
    # Connects the logger to the root logging handler; 
    # by default this captures
    # all logs at INFO level and higher
    client.setup_logging()
