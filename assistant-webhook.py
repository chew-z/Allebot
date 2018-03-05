# -*- coding: utf-8 -*-
import logging
from flask import Flask
from zeep import Client
import configparser
import os
config = configparser.ConfigParser()
config.read('allegro.conf')
google_conf = config['Google']
os.environ['DEV_ACCESS_TOKEN'] = google_conf['DEV_ACCESS_TOKEN']
os.environ['CLIENT_ACCESS_TOKEN'] = google_conf['CLIENT_ACCESS_TOKEN']

from flask_assistant import Assistant, ask, tell, build_item


app = Flask(__name__)
app.config['ASSIST_ACTIONS_ON_GOOGLE'] = True
assist = Assistant(app, route='/')
logging.getLogger('flask_assistant').setLevel(logging.DEBUG)


allegro_conf = config['Allegro']

countryId = 1
webAPI = allegro_conf['WEB_API_KEY']
url = allegro_conf['WEB_API_WSDL']
client = Client(url)


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


@assist.action('Default Welcome Intent')
def welcome():
    speech = 'Welcome to Allegro shopping on Google Assistant!'
    return ask(speech).reprompt('Do you want to see examples?').suggest('Search iphone', 'Search macbook')


@assist.action('Default Welcome Intent - yes')
def action_func():
    speech = """What would you like to search for?.
                    Make your choice!"""

    return ask(speech).suggest('iPhone', 'MacBook')


@assist.action('SearchIphone')
# show results in Carousel
def action_func():
    resp = ask('Here are some iPhones I have found on Allegro').build_carousel()
    searchResult = alleSearch('iPhone', size=3)
    i = 0
    for item in searchResult:
        i += 1
        resp.add_item("{} zł".format(item['cena']), 
                key='option {}'.format(i),
                img_url=item['zdjęcie'],
                description=item['aukcja'])
    
    return resp



@assist.action('SearchMacbook')
def action_func():

    # Basic speech/text response
    resp = ask("Let me show you some Macbooks available")
    searchResult = alleSearch('Macbook', size=3)

    # Create a list with a title
    mylist = resp.build_list('Macbook')
    i = 0
    for item in searchResult:
        i += 1
        mylist.add_item("{} zł".format(item['cena']), 
                key='option {}'.format(i),
                img_url=item['zdjęcie'],
                description=item['aukcja'],
                synonyms=[])

    return mylist

@assist.action('SearchAnything', mapping={'search_item': 'sys.any'})
def action_func(search_item):

    # Basic speech/text response
    resp = ask("Let's see what is available")
    searchResult = alleSearch("{}".format(search_item), size=5)

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
