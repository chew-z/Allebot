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
from zeep.cache import SqliteCache
from zeep.transports import Transport
import json
from pathlib import Path
import argparse
import configparser
import logging
import logging.config
import os

config = configparser.ConfigParser()
config.read('allebot.conf')
allegro_conf = config['Allegro']

countryId = 1
webAPI = allegro_conf['WEB_API_KEY']
url = allegro_conf['WEB_API_WSDL']
client = Client(url)


app = Flask(__name__)
# https://stackoverflow.com/questions/36378441/
# preserve Unicode in jsonify
app.config['JSON_AS_ASCII'] = False


def alleKategorieGet():
  ''' Get list of all categories from file if exists
      and if not call WebAPI
  '''
  if Path("kategorie.json").is_file():
    # file exists
    logging.info('kategorie.json exists')
    j = json.load(open('kategorie.json'))
  else:
    # call WebAPI
    logging.info('Couldn\'t find kategorie.json - getting from WebAPI')
    wynik = client.service.doGetCatsData(webapiKey=webAPI, countryId=countryId, onlyLeaf=False)
    categories = wynik['catsList']['item']
    j = [{"catId": i['catId'], "catName": i['catName'], "catParent": i['catParent'], "catPosition": i['catPosition']} for i in categories]
    with open('kategorie.json', 'w') as outfile:
      json.dump(j, outfile)
    logging.info('Categories saved to kategorie.json')

  return(j)

def alleKategoriaNazwa(categories, id):
  ''' Returns category name from id
  '''
  return [x for x in categories if x['catId'] == id][0]['catName']


def alleKategorieBranch(categories, id):
  ''' Warning: Recursion!
      Get entire branch (sequence of parent categories up to root) for a category (id).
      root category is '0'
  '''
  up = [ x for x in categories if x['catId'] == id ]
  if not up:
    # stop recursion - upper branch is None
    return ''
  elif id == '0':
    # stop recursion we have reach root
    return ''
  else:
    # continue recursive pattern following the branch
    # logging.debug("itemId {} - up - {}".format(id, up[0]))
    return "{}({}) - {}".format(up[0]['catName'], up[0]['catId'], alleKategorieBranch(categories, up[0]['catParent']))


def alleCreateFilters(filtersList):
  ''' Creates ns0:ArrayOfFilteroptionstype object from list 
      of search parameters (filters). 
      This is essential for narrowing search results down to precise categories 
      but at the same time full of traps due to awkard implementations.
      Allegro Webapi requires nested arrays and it could be tricky with zeep
      because when using naive dictionary zeep will quietly ignore elements 
      that should be put into arrays (will take last element from list or so) 
      and you will never find out at a glance.
      (look at soap envelope in logs with DEBUG option to confirm filters are on).
      https://github.com/mvantellingen/python-zeep/issues/145
      Allegro will ignore multiple categories in one call (so what is array for?)
      https://allegro.pl/webapi/tutorials.php/tutorial/id,281 [see comments]
  '''
  factory = client.type_factory('ns0')
  filterArrayPlaceholder = client.get_type('ns0:ArrayOfFilteroptionstype')
  filters = filterArrayPlaceholder()
  for key, value in filtersList.items():
      logging.info("filters: {} = {}".format(key, value))
      optionsArrayPlaceholder = client.get_type('ns0:FilterOptionsType')
      option = optionsArrayPlaceholder()
      AOSPlaceholder = client.get_type('ns0:ArrayOfString')
      AOS = AOSPlaceholder()
      # TODO - should be iteration for multiple values in list
      # or better extend() in place of append() if 'value' would be an array
      AOS['item'].append(value)
      option['filterId'] = key
      option['filterValueId'] = AOS
      filters['item'].append(option)           
      
  logging.info("ArrayOfFilteroptionstype object: {}".format(filters))
  
  return filters 


def alleSearch(q, category, size=5):
  ''' Wrapper for doGetItemsList() method with filters and parameters '''
  filterOptionsList = {'category': str(category),
                        'search': q,
                        'condition': 'used'
                      }
  filters = alleCreateFilters(filterOptionsList)
  wynik = client.service.doGetItemsList(
      webAPI, countryId, filterOptions=filters, resultScope=3, resultSize=size)
  
  logging.info("Otrzymano %d wynikow." % wynik.itemsCount)
  # TODO - figure out how to display filters....
  logging.info("filtersList: {}".format(wynik.filtersList))
  logging.info("filtersRejected: {}".format(wynik.filtersRejected))
  logging.info("categoriesList: {}".format(wynik.categoriesList))

  _results = list()
  if wynik.itemsList is not None:
      # get ready list of categories
      listOfCategories = alleKategorieGet()
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
              'gałąź': alleKategorieBranch(listOfCategories, item.categoryId),
              'id': item.itemId,
              'kategoria': "{} ({})".format(alleKategoriaNazwa(listOfCategories, item.categoryId), item.categoryId),
              'link': 'https://allegro.pl/i' + str(item.itemId) + '.html',
              'typ aukcji': typAukcji,
              'zdjęcie': item.photosInfo['item'][0]['photoUrl']
          }
          _results.append(d)
  logging.info("{}".format(_results))
  return(_results)


@app.route("/")
def hello():
    return "Hello World!"


@app.route('/search')
def search():
    query = request.args.get('q', default = 'iphone', type = str)
    category = request.args.get('cat', default = 2, type = int)
    # condition = request.args.get('condition', default = 'used', type = str)
    size = request.args.get('size', default = 5, type = int)
    logging.info("{} {} {}".format(query, category, size))
    result = alleSearch(query, category, size)
    
    return(jsonify(result))


if __name__ == "__main__":
    FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
    try:
        os.remove('allequery.log')
    except BaseException:
        pass
    logging.basicConfig(filename='allequery.log', level=logging.DEBUG,
            format=FORMAT, datefmt='%a, %d %b %Y %H:%M:%S', )
    # Turn off default zeep.transports DEBUG logging
    logging.getLogger('zeep.transports').setLevel(logging.INFO)
    logging.info('--- logging started ---.')

    app.run(debug=True, port=8080)

    logging.info('--- logging finished ---.')


