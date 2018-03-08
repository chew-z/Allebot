#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Test of Google AppEngine
simple webhook for searching Allegro
- via Allegro Web API
- uses zeep
- returns item url
'''
from flask import Flask, request
from flask.json import jsonify
from zeep import Client
import configparser
import logging
import os

config = configparser.ConfigParser()
config.read('allegro.conf')
allegro_conf = config['Allegro']

countryId = 1
webAPI = allegro_conf['WEB_API_KEY']
url = allegro_conf['WEB_API_WSDL']
client = Client(url)


app = Flask(__name__)
# https://stackoverflow.com/questions/36378441/
# preserve Unicode in jsonify
app.config['JSON_AS_ASCII'] = False

@app.route("/")
def hello():
    return "Hello World!"


@app.route('/search')
def search():
    query = request.args.get('q', default = 'iphone', type = str)
    category = request.args.get('cat', default = 2, type = int)
    condition = request.args.get('condition', default = 'used', type = str)
    size = request.args.get('size', default = 5, type = int)
    logging.info("{} {} {} {}".format(query, category, condition, size))
    result = alleSearch(query, category, condition, size)
    return(jsonify(result))


def alleSearch(q, category, condition, size):

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
                    'link': 'https://allegro.pl/i' + str(item.itemId) + '.html',
                    'typ aukcji': typAukcji,
                    'zdjęcie': item.photosInfo['item'][0]['photoUrl']
                    }
            l.append(d)
    print(l)
    return(l)



if __name__ == "__main__":
    FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
    try:
        os.remove('allequery.log')
    except BaseException:
        pass
    logging.basicConfig(filename='allequery.log', level=logging.DEBUG,
            format=FORMAT, datefmt='%a, %d %b %Y %H:%M:%S',)
    logging.info('--- logging started ---.')

    app.run(debug=True, port=8080)

    logging.info('--- logging finished ---.')


