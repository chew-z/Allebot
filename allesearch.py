from zeep import Client
from zeep.cache import SqliteCache
from zeep.transports import Transport
from pathlib import Path
import configparser
import json
import logging

from allehelp import isAppEngine

logger = logging.getLogger('allebot')
if not isAppEngine():
    logger.addHandler(logging.StreamHandler())
    if logger.level == logging.NOTSET:
        logger.setLevel(logging.INFO)

config = configparser.ConfigParser()
config.read('allebot.conf')

webAPI = config['Allegro']['WEB_API_KEY']
url = config['Allegro']['WEB_API_WSDL']
countryId = 1

if isAppEngine():
    # Can't use sql cache on AppEngine
    # https://github.com/mvantellingen/python-zeep/issues/243
    client = Client(url, transport=Transport(cache=None))
else:
    cache = SqliteCache(path='/tmp/dialog-webhook_zeep_sqlite.db', timeout=60)
    transport = Transport(cache=cache)
    client = Client(url, transport=transport)


def alleKategorieGet():
  ''' Get list of all categories from file if exists
      and if not call WebAPI
  '''
  if Path("kategorie.json").is_file():
    # file exists
    logger.debug('kategorie.json exists')
    j = json.load(open('kategorie.json'))
  else:
    # call WebAPI
    logger.debug('Couldn\'t find kategorie.json - getting from WebAPI')
    wynik = client.service.doGetCatsData(webapiKey=webAPI, countryId=countryId, onlyLeaf=False)
    categories = wynik['catsList']['item']
    j = [{"catId": i['catId'], "catName": i['catName'], "catParent": i['catParent'], "catPosition": i['catPosition']} for i in categories]
    with open('kategorie.json', 'w') as outfile:
      json.dump(j, outfile)
    logger.debug('Categories saved to kategorie.json')

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
    logger.debug("itemId {} - up - {}".format(id, up[0]))
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
      logger.info("filters: {} = {}".format(key, value))
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
      
  logger.debug("ArrayOfFilteroptionstype object: {}".format(filters))
  
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
  
  logger.debug("Otrzymano %d wynikow." % wynik.itemsCount)
  # TODO - figure out how to display filters....
  logger.debug("filtersList: {}".format(wynik.filtersList))
  logger.debug("filtersRejected: {}".format(wynik.filtersRejected))
  logger.debug("categoriesList: {}".format(wynik.categoriesList))

  _results = list()
  if wynik.itemsList is not None:
      # get ready list of categories
      listOfCategories = alleKategorieGet()
      for item in wynik.itemsList['item']:
          logger.debug("{} --- {} --- {}".format(item.itemTitle,
                                                 item.timeToEnd, item.priceInfo['item'][0]['priceValue']))
          logger.debug('https://allegro.pl/i' + str(item.itemId) + '.html')
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
  logger.debug("{}".format(_results))
  return(_results)
