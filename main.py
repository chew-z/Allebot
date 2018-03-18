# -*- coding: utf-8 -*-
import configparser
import logging
import os

from allesearch import alleSearch
from allehelp import _debug, _info, _error, isAppEngine, use_logging_handler

from flask import Flask, request
from flask.json import jsonify

import configparser
config = configparser.ConfigParser()
config.read('allebot.conf')
os.environ['DEV_ACCESS_TOKEN'] = config['Google']['DEV_ACCESS_TOKEN']
os.environ['CLIENT_ACCESS_TOKEN'] = config['Google']['CLIENT_ACCESS_TOKEN']
from flask_assistant import Assistant, ask, tell, build_item
from flask_assistant import context_manager
from flask_assistant import logger

app = Flask(__name__)
# https://stackoverflow.com/questions/36378441/
# preserve Unicode in jsonify
app.config['JSON_AS_ASCII'] = False
app.config['ASSIST_ACTIONS_ON_GOOGLE'] = True

assist = Assistant(app, route='/')

if isAppEngine():
    use_logging_handler()


@assist.action('Default Welcome Intent')
def welcome():
    speech = 'Welcome to Allegro shopping!'
    return ask(speech).reprompt('Do you want to see examples?').suggest(
        'I want new smartphone', 'I am looking for a laptop', 'Looking for bike')


@assist.action('Welcome')
def welcome():
    speech = 'Welcome to Allegro shopping! You want to search for smartphone, laptop, or bike?'
    return ask(speech)


@assist.action('Declare-category')
def search_category(search_category):
    speech = "Ok, you chose {} right?".format(search_category)
    context_manager.add('search_context', lifespan=5)
    context_manager.set('search_context', 'search_category', search_category) 
    return ask(speech)


@assist.action('Confirm-category')
def confirm_category(category_confirmation):
    category = context_manager.get_param('search_context', 'search_category')
    _debug("Confirm-category: category: {}".format(category))
    if 'n' in category_confirmation:
        return ask('I dont think I understood. What do you want to look for?').suggest(
        'smartphone', 'laptop', 'bike')
    else:
        return ask('OK. What exactly are you looking for?')


@assist.action('SearchAnything', mapping={'search_item': 'sys.any'})
def action_func(search_item):
    category = context_manager.get_param('search_context', 'search_category')
    _debug('search_category: --{}--'.format(category))
    sc = 0
    if category == 'bike':
        sc = 3919
    elif category == 'laptop':
        sc = 491
    elif category == 'smartphone':
        sc = 165
    else:
        sc = 0
    # Basic speech/text response
    resp = ask("Let's see what is available")
    searchResult = alleSearch("{}".format(search_item), category=sc, size=10)

    # Create a list with a title
    mylist = resp.build_list('Results')
    i = 0
    for item in searchResult:
        i += 1
        mylist.add_item("{} zł".format(item['cena']),
                        key='option {}'.format(i),
                        img_url=item['zdjęcie'],
                        description=item['aukcja'],
                        synonyms=[])

    return mylist


@app.route('/hello')
def test_page():
    _info('/hello')
    return "Hello World from dialog-webhook.py"


@app.route('/search')
def search():
    _info('/search')
    query = request.args.get('q', default = 'iphone', type = str)
    category = request.args.get('cat', default = 48978, type = int)
    # condition = request.args.get('condition', default = 'used', type = str)
    size = request.args.get('size', default = 10, type = int)
    _debug("{} {} {}".format(query, category, size))
    result = alleSearch(query, category, size)
    
    return(jsonify(result))


@app.errorhandler(500)
def server_error(e):
    logger.exception('An error occurred during a request.')
    return """
    An internal error occurred: <pre>{}</pre>
    See logs for full stacktrace.
    """.format(e), 500


if __name__ == '__main__':
    # This is used when running locally. Gunicorn is used to run the
    # application on Google App Engine. See entrypoint in app.yaml.
    # flask app.debug=True in development only (not a good idea on GAE)
    app.debug = True
    try:
        os.remove('allebot.log')
    except BaseException:
        pass
    FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
    logging.basicConfig(filename='allebot.log', level=logging.DEBUG,
            format=FORMAT, datefmt='%a, %d %b %Y %H:%M:%S', )    
    # Turn off default zeep.transports DEBUG logging
    logging.getLogger('zeep.transports').setLevel(logging.INFO)
    logging.getLogger('flask_assistant').setLevel(logging.DEBUG)
    _info('--- logging started ---.')
    app.run(port=8080)
    _info('--- logging finished ---.')
