# -*- coding: utf-8 -*-
import logging
from flask import Flask
from zeep import Client
from zeep.cache import SqliteCache
from zeep.transports import Transport
import configparser
import json
import os
from pathlib import Path
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
client = Client(url, transport=transport)


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
    logging.debug("itemId {} - up - {}".format(id, up[0]))
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
def confirm_category(category_confirmation):
    category = context_manager.get_param('search_context', 'search_category')
    print("Confirm-category: category: {}".format(category))
    if 'n' in category_confirmation:
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
