import configparser
import logging
import os

from allesearch import alleSearch
from allehelp import isAppEngine

from flask import Flask, request
from flask.json import jsonify

config = configparser.ConfigParser()
config.read('allebot.conf')
os.environ['DEV_ACCESS_TOKEN'] = config['Google']['DEV_ACCESS_TOKEN']
os.environ['CLIENT_ACCESS_TOKEN'] = config['Google']['CLIENT_ACCESS_TOKEN']
from flask_assistant import Assistant, ask, tell
from flask_assistant import context_manager


app = Flask(__name__)
# https://stackoverflow.com/questions/36378441/
# preserve Unicode in jsonify
app.config['JSON_AS_ASCII'] = False
app.config['ASSIST_ACTIONS_ON_GOOGLE'] = True
# TODO - perhaps specify different route for flask_assistant webhook
assist = Assistant(app, route='/')

logger = logging.getLogger('allebot')
if isAppEngine():
    logger.addHandler(logging.StreamHandler())
    if logger.level == logging.NOTSET:
        logger.setLevel(logging.DEBUG)


@assist.action('Welcome')
def welcome():
    return ask('Welcome to Allegro shopping!').suggest(
        'I want new smartphone', 'I am looking for a laptop', 'Looking for bike')


@assist.action('Start')
def start_conversation(search_category):
    context_manager.add('search_context', lifespan=5)
    context_manager.set('search_context', 'search_category', search_category)
    return ask("Hello shopper!, you looking for {} right?".format(
        search_category)).suggest('yes', 'no')


@assist.action('Restart')
def restart_conversation():
    context_manager.add('search_context', lifespan=0)
    context_manager.add('search_results', lifespan=0)
    return ask('OK! New search').suggest(
        'I want new smartphone', 'I am looking for a laptop', 'Looking for bike')


@assist.action('End')
def end_conversation():
    return tell('Thank you for your visit! Please come back')


@assist.action('Declare_Category')
def search_category(search_category):
    context_manager.add('search_context', lifespan=5)
    context_manager.set('search_context', 'search_category', search_category)
    return ask("OK, you looking for {} right?".format(
        search_category)).suggest('yes', 'no')


@assist.action('Confirm_Category')
def confirm_category(category_confirmation):
    category = context_manager.get_param('search_context', 'search_category')
    logger.debug("Confirm-category: category: {}".format(category))
    if 'n' in category_confirmation:
        return ask('What do you want to look for then?').suggest(
            'smartphone', 'laptop', 'bike')
    else:
        # Suggest search based on category context
        if category == 'bike':
            return ask('OK. What exactly are you looking for?').suggest(
                'find me peugeot', 'search koga miyata', 'search for bianchi')
        elif category == 'laptop':
            return ask('OK. What exactly are you looking for?').suggest(
                'find me macbook pro', 'search x230', 'search for dell xps')
        elif category == 'smartphone':
            return ask('OK. What exactly are you looking for?').suggest(
                'find me iphone 8', 'search xperia xz', 'search galaxy')
        else:
            return ask('OK. What exactly are you looking for?')


@assist.action('Search_Anything', mapping={'search_item': 'sys.any'})
def search_anything(search_item):
    synonyms_list = [['one', 'first'], ['two', 'second'], ['three', 'third'], ['four', 'fourth'],
                     ['five', 'fifth'], ['six', 'sixth'], ['seven', 'seventh'], ['eight'], ['nine'], ['ten']]
    category = context_manager.get_param('search_context', 'search_category')
    logger.debug('search_category: --{}--'.format(category))
    sc = 0
    # TODO - this is crucial part - associating category with right category
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
    searchResult = alleSearch("{}".format(search_item), category=sc, size=5)
    logger.debug("{}".format(searchResult))
    context_manager.add('search_results', lifespan=5)
    context_manager.set('search_results', 'search_result', searchResult)
    # Create a list with a title
    mylist = resp.build_list('Results')
    i = 0
    for item in searchResult:
        i += 1
        mylist.add_item(title="option {}".format(synonyms_list[i - 1][0]),  # title sent as query for Actions
                        # key sent as query for API.AI
                        key='option {}'.format(i),
                        img_url=item['zdjęcie'],
                        description="{} zł {}".format(
                            item['cena'], item['aukcja']),
                        synonyms=synonyms_list[i - 1])

    return mylist


@assist.action('Select_Item', mapping={'number': 'sys.number'})
def select_item(number):
    logger.debug("{}".format(number))
    searchResult = context_manager.get_param('search_results', 'search_result')
    # logger.debug("{}".format(searchResult))
    item = searchResult[int(number)]
    logger.debug("{}".format(item))
    resp = tell("Here's your choice {}".format(number))
    # resp.card(text='{}'.format(item['cena']),
    #           title='{} zł {}'.format(item['cena'], item['aukcja']),
    #           img_url='{}'.format(item['zdjęcie'])
    #           )

    return resp


@app.route('/hello')
# simpliest health check possible
def test_page():
    logger.info('/hello')
    return "Hello World from dialog-webhook.py"


@app.route('/search')
# webhook for testing search
def search():
    logger.info('/search')
    query = request.args.get('q', default='iphone', type=str)
    category = request.args.get('cat', default=48978, type=int)
    # condition = request.args.get('condition', default = 'used', type = str)
    size = request.args.get('size', default=10, type=int)
    logger.debug("{} {} {}".format(query, category, size))
    result = alleSearch(query, category, size)

    return(jsonify(result))


@app.errorhandler(500)
# TODO - make more useful - this is just placeholder
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
    logging.getLogger('allebot').setLevel(logging.INFO)  # TODO
    logging.info('--- logger.started ---.')
    app.run(port=8080)
    logging.info('--- logger.finished ---.')
