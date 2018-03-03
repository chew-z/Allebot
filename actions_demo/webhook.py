# -*- coding: utf-8 -*-
import logging
from flask import Flask
from flask_assistant import Assistant, ask, tell, build_item
from zeep import Client
import configparser
import logging
import os

app = Flask(__name__)
app.config['ASSIST_ACTIONS_ON_GOOGLE'] = True
assist = Assistant(app, route='/')
logging.getLogger('flask_assistant').setLevel(logging.DEBUG)

config = configparser.ConfigParser()
config.read('allegro.conf')
allegro_conf = config['Allegro']

countryId = 1
webAPI = allegro_conf['WEB_API_KEY']
url = allegro_conf['WEB_API_WSDL']
client = Client(url)

google_conf = config['Google']
os.environ['DEV_ACCESS_TOKEN'] = google_conf['DEV_ACCESS_TOKEN']
os.environ['CLIENT_ACCESS_TOKEN'] = google_conf['CLIENT_ACCESS_TOKEN']


def alleSearch(q, category=2, condition='used', size=5):

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
            logging.info("{} --- {} --- {}".format(item.itemTitle, item.timeToEnd, item.priceInfo['item'][0]['priceValue']))
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
    print(l)
    return(l)


# @assist.action('Default Welcome Intent')
# def welcome():
#     speech = 'Welcome to Allegro shopping on Google Assistant!'
#     return ask(speech).reprompt('Do you want to see examples?').suggest('iphone', 'macbook')


# @assist.action('Default Welcome Intent - yes')
# def action_func():
#     speech = """What would you like to search for?.
#                     Make your choice!"""

#     return ask(speech).suggest('Search iPhone', 'Search MacBook')


@assist.action('SearchIphone')
# show results in Carousel
def action_func():
    resp = ask('Here are some iPhones I have found on Allegro').build_carousel()
    searchResult = alleSearch('iPhone', size=3)

    for item in searchResult:
        resp.add_item(item['cena'], key=item['id'],
                  description=item['aukcja'],
                  img_url=item['zdjęcie'])

    # resp.add_item('API.AI',
    #               key='api.ai',
    #               description=API_DESCRIPT,
    #               img_url=API_LOGO_URL)
    return resp



@assist.action('SearchMacbook')
def action_func():

    # Basic speech/text response
    resp = ask("Let me show you some Macbooks available")
    searchResult = alleSearch('Macbook', size=3)

    # Create a list with a title
    mylist = resp.build_list('Macbook')
    for item in searchResult:
        # Add items directly to list
        mylist.add_item(item['cena'],
                    key=item['id'],  # query sent if item selected
                    img_url=item['zdjęcie'],
                    description=item['aukcja'],
                    synonyms=['flask assistant', 'number one', 'assistant', 'carousel'])

    # mylist.add_item('Flask-Ask',
    #                 key='flask_ask',
    #                 img_url=ASK_LOGO_URL,
    #                 description='Rapid Alexa Skills Kit Development for Amazon Echo Devices',
    #                 synonyms=['ask', 'flask ask', 'number two'])

    return mylist


if __name__ == '__main__':
    app.run(debug=True)
