'''
Searching for items via Web API 
- uses zeep
- returns item url
'''
from zeep import Client
import configparser

config = configparser.ConfigParser()
config.read('allegro.conf')
allegro_conf = config['Allegro']

countryId = 1
webAPI = allegro_conf['WEB_API_KEY']
url = allegro_conf['WEB_API_WSDL']
client = Client(url)

filterOptionsList = {'item':
                     {'filterId': 'category',
                      'filterValueId': ['2']  # Nieruchomosci
                      },
                     'item':
                         {'filterId': 'condition',
                          'filterValueId': 'used'
                          },
                     'item':
                         {'filterId': 'search',
                          'filterValueId': 'iphone'
                          }
                     }

def magicDecode(var):
    """Decode unicode to string."""
    if var:
        var = var.encode('utf8')
    return var


wynik = client.service.doGetItemsList(
    webAPI, countryId, filterOptions=filterOptionsList, resultScope=3, resultSize=10)
print("Otrzymano %d wynikow." % wynik.itemsCount)
for item in wynik.itemsList['item']:
    print(item.itemTitle, '---', item.timeToEnd, '---', item.priceInfo['item'][0]['priceValue'])
    print('https://allegro.pl/i' + str(item.itemId) + '.html')
    print(item.photosInfo['item'][0]['photoUrl'])
