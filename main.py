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


config = configparser.ConfigParser()
config.read('allegro.conf')
allegro_conf = config['Allegro']

countryId = 1
webAPI = allegro_conf['WEB_API_KEY']
url = allegro_conf['WEB_API_WSDL']
client = Client(url)


app = Flask(__name__)


@app.route("/")
def hello():
    return "Hello World!"


@app.route('/search')
def search():
    category = request.args.get('cat', default = 2, type = int)
    condition = request.args.get('condition', default = 'used', type = str)
    search = request.args.get('q', default = 'iphone', type = str)
    result = alleSearch(category, condition, search)
    return(jsonify(result))

def alleSearch(category='2', condition='used', search='iphone'):

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
                'filterValueId': search
                }
            }

    wynik = client.service.doGetItemsList(
            webAPI, countryId, filterOptions=filterOptionsList, resultScope=3, resultSize=10)
    logging.info("Otrzymano %d wynikow." % wynik.itemsCount)
    l = list()
    for item in wynik.itemsList['item']:
        logging.info(item.itemTitle, '---', item.timeToEnd, '---', item.priceInfo['item'][0]['priceValue'])
        logging.info('https://allegro.pl/i' + str(item.itemId) + '.html')
        d = { 
                'aukcja': item.itemTitle,
                u'czas do końca': item.timeToEnd,
                'aktualna cena': item.priceInfo['item'][0]['priceValue'],
                'link': 'https://allegro.pl/i' + str(item.itemId) + '.html'
                }
        l.append(d)

    return(l)



if __name__ == "__main__":
    FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
    try:
        os.remove('allesearch.log')
    except BaseException:
        pass
    logging.basicConfig(filename='allesearch.log', level=logging.DEBUG,
            format=FORMAT, datefmt='%a, %d %b %Y %H:%M:%S',)
    logging.info('--- logging started ---.')

    app.run(debug=True, port=8080)

    logging.info('--- logging finished ---.')


