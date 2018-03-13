# -*- coding: utf-8 -*-
import logging
from flask import Flask
from zeep import Client
from zeep.cache import SqliteCache
from zeep.transports import Transport
import configparser
import os
config = configparser.ConfigParser()
config.read('allegro.conf')
google_conf = config['Google']
os.environ['DEV_ACCESS_TOKEN'] = google_conf['DEV_ACCESS_TOKEN']
os.environ['CLIENT_ACCESS_TOKEN'] = google_conf['CLIENT_ACCESS_TOKEN']
# Dialogflow agent tokens need to be set at flask_assistant import 
from flask_assistant import Assistant, ask, tell, build_item
from flask_assistant import context_manager

app = Flask(__name__)
app.config['ASSIST_ACTIONS_ON_GOOGLE'] = True
assist = Assistant(app, route='/')
logging.getLogger('flask_assistant').setLevel(logging.INFO)
logging.getLogger('zeep.transports').setLevel(logging.INFO)

allegro_conf = config['Allegro']
countryId = 1
webAPI = allegro_conf['WEB_API_KEY']
url = allegro_conf['WEB_API_WSDL']

cache = SqliteCache(path='/tmp/dialog-webhook_zeep_sqlite.db', timeout=60)
transport = Transport(cache=cache)
# transport = Transport(cache=SqliteCache())
client = Client(url, transport=transport)
# client = Client(url)


def alleSearch(q, category, condition='used', size=5):
    print('alleSearch: q={}, category={}'.format(q, category))
    filterOptionsList = {'item':
                         {'filterId': 'category',
                          'filterValueId': [category]
                          },
                         'item':
                         {'filterId': 'condition',
                          'filterValueId': condition
                          },
                         'item':
                         {'filterId': 'search',
                          'filterValueId': q
                          }
                         }

    wynik = client.service.doGetItemsList(
        webAPI, countryId, filterOptions=filterOptionsList, resultScope=3, resultSize=size)
    logging.info("Otrzymano %d wynikow." % wynik.itemsCount)
    l = list()
    if wynik.itemsList is not None:
        for item in wynik.itemsList['item']:
            logging.info("{} --- {} --- {}".format(item.itemTitle,
                                                   item.timeToEnd, item.priceInfo['item'][0]['priceValue']))
            logging.info('https://allegro.pl/i' + str(item.itemId) + '.html')
            typAukcji = ''
            if item.priceInfo['item'][0]['priceType'] == 'buyNow':
                typAukcji = 'kup teraz'
            else:
                typAukcji = 'aukcja'
            d = {
                'aukcja': item.itemTitle,
                'cena': item.priceInfo['item'][0]['priceValue'],
                'czas do końca': item.timeToEnd,
                'id': item.itemId,
                'link': 'https://allegro.pl/i' + str(item.itemId) + '.html',
                'typ aukcji': typAukcji,
                'zdjęcie': item.photosInfo['item'][0]['photoUrl']
            }
            l.append(d)
    logging.info(l)
    return(l)


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
    context_manager.add('search_context', lifespan=3)
    context_manager.set('search_context', 'search_category', search_category) 
    return ask(speech)


@assist.action('Confirm-category')
def confirm_category(answer):
    category = context_manager.get_param('search_context', 'search_category')
    print("Confirm-category: category: {}".format(category))
    if 'n' in answer:
        return ask('I dont think I understood. What do you want to look for?').suggest(
        'smartphone', 'laptop', 'bike')
    else:
        return ask('OK. What exactly are you looking for?')


@assist.action('SearchAnything', mapping={'search_item': 'sys.any'})
def action_func(search_item):
    category = context_manager.get_param('search_context', 'search_category')
    print('search_category: --{}--'.format(category))
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
    searchResult = alleSearch("{}".format(search_item), category=sc, size=5)

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


if __name__ == '__main__':
    app.run(debug=True)
