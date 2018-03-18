import logging
import os


def isAppEngine():
    server = os.getenv('SERVER_SOFTWARE', '')
    if server is not None and server.startswith('Google App Engine/'): 
        return True 
    else: 
        return False


def use_logging_handler():
    # Imports the Google Cloud client library
    import google.cloud.logging
    # Instantiates a client
    client = google.cloud.logging.Client()
    # Connects the logger to the root logging handler; 
    # by default this captures
    # all logs at INFO level and higher
    client.setup_logging()
    logging.getLogger('allebot').addHandler(logging.StreamHandler())
    logging.getLogger('allebot').setLevel(logging.INFO)
