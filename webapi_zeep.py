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
import configparser
import logging
import logging.config
import pprint

config = configparser.ConfigParser()
config.read('allegro.conf')
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
  if Path("kategorie.json").is_file():
    # file exists
    logging.info('kategorie.json exists')
    j = json.load(open('kategorie.json'))
  else:
    wynik = client.service.doGetCatsData(webapiKey=webAPI, countryId=countryId, onlyLeaf=False)
    w = wynik['catsList']['item']
    j = [{"catId": i['catId'], "catName": i['catName'], "catParent": i['catParent'], "catPosition": i['catPosition']} for i in w]
    with open('kategorie.json', 'w') as outfile:
      json.dump(j, outfile)
    logging.info('Categories saved to kategorie.json')

  return(j)

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
    # print(l)
    return(l)

def alleKategorieAll():
  wynik = client.service.doGetCatsData(webapiKey=webAPI, countryId=countryId, onlyLeaf=False)

  return(wynik['catsList']['item'])
  
def alleKategorieParent(wynik, parent):
  return([i for i in wynik if i['catParent'] == parent ])


def alleKategorieName(wynik, name):
  return([i for i in wynik if name in i['catName'] ])


def alleKategorieParentName(wynik, name):
  # categories whose parent has 'name'
  parents = [i for i in wynik if name in i['catName'] ]
  l = []
  for p in parents:
    x = [i for i in wynik if i['catParent'] == p['catId'] ]
    l.extend(x)
  
  return(l)


def alleKategorieFuzzyName(wynik, name):
  # TODO: come up with something clever
  # categories whos have 'name' or parent with 'name'
  parents_with_name = [i for i in wynik if name in i['catName'] ]
  children_with_name = [i for i in wynik if name in i['catName'] ]
  l = children_with_name.extend(parents_with_name)
  return(l)


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
    l = alleSearch(q='iphone')
    # l = alleKategorieAll()
    # kategorie = alleKategorieGet()
    
    # l = alleKategorieParent(w, 0)
    # pp.pprint(l)
    # lista_kategorii = alleKategorieName(j, 'Lenovo')
    pp.pprint(l)
    # for i in l:
    #   p = [ p['catName'] for p in j if i['catParent'] == p['catId'] ][0]
    #   # print(p)
    #   print("{} -- {} -- {}, {} -- {}".format(i['catId'], i['catName'], i['catParent'], p, i['catPosition']))

    logging.info('--- logging finished ---.')
