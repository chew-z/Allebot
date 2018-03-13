'''
Searching for items, categories via Web API 
- experimenting, testing methods
- uses zeep
- returns item url
'''
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
import pprint

config = configparser.ConfigParser()
config.read('allebot.conf')
allegro_conf = config['Allegro']

countryId = 1
webAPI = allegro_conf['WEB_API_KEY']
url = allegro_conf['WEB_API_WSDL']
# use 60 minutes zeep caching backend
cache = SqliteCache(path='/tmp/webapi_zeep_sqlite.db', timeout=60)
transport = Transport(cache=cache)
# transport = Transport(cache=SqliteCache())
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


# def alleKategorieAll():
#   ''' Get list of categories from WebAPI 
#       TODO - remove, replaced with alleKategorieGet()
#   '''
#   wynik = client.service.doGetCatsData(webapiKey=webAPI, countryId=countryId, onlyLeaf=False)
#   return(wynik['catsList']['item'])
  

# def alleKategorieParent(categories, parent):
#   return([i for i in categories if i['catParent'] == parent ])


# def alleKategorieName(categories, name):
#   ''' Categories whose category name in 'name' '''
#   return([i for i in categories if name in i['catName'] ])


# def alleKategorieParentName(categories, name):
#   ''' Categories whose parent has 'name' '''
#   parents = [i for i in categories if name in i['catName'] ]
#   l = []
#   for p in parents:
#     x = [i for i in categories if i['catParent'] == p['catId'] ]
#     l.extend(x)
  
#   return(l)


# def alleKategorieFuzzyName(categories, name):
#   ''' TODO: what is it for? Is it still necessary/usefull?
#   categories who have 'name' or parent with 'name'
#   '''
#   parents_with_name = [i for i in categories if name in i['catName'] ]
#   children_with_name = [i for i in categories if name in i['catName'] ]
#   l = children_with_name.extend(parents_with_name)
#   return(l)


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


def getArgs(argv=None):
  parser = argparse.ArgumentParser(description='Saves ft.com articles \
                   [from Chrome via service] as markdown and html preview',
                                   formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument('-q', '--query', default=None,
                      help='Search query')
  parser.add_argument('-c', '--category',
                      help='Search category')
  parser.add_argument('-i', '--items', default=5,
                      help='Number of search resuls')
  return parser.parse_args(argv)


if __name__ == "__main__":
  FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
  try:
      os.remove('webapi_zeep.log')
  except BaseException:
      pass
  logging.basicConfig(filename='webapi_zeep.log', level=logging.DEBUG,
          format=FORMAT, datefmt='%a, %d %b %Y %H:%M:%S',)
  # Turn off default zeep.transports DEBUG logging
  logging.getLogger('zeep.transports').setLevel(logging.INFO)
  logging.info('--- logging started ---.')
  
  pp = pprint.PrettyPrinter(indent=4)
  args = getArgs()
  l = alleSearch(q=args.query, category=args.category, size=args.items)
  pp.pprint(l)

  logging.info('--- logging finished ---.')
    # l = alleKategorieAll()
    # kategorie = alleKategorieGet()
    
    # l = alleKategorieParent(w, 0)
    # pp.pprint(l)
    # lista_kategorii = alleKategorieName(j, 'Lenovo')
    # pp.pprint(l)
    # for i in l:
    #   p = [ p['catName'] for p in j if i['catParent'] == p['catId'] ][0]
    #   # print(p)
    #   print("{} -- {} -- {}, {} -- {}".format(i['catId'], i['catName'], i['catParent'], p, i['catPosition']))

    
