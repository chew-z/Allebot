'''
Simple FB Messenger weatherbot - as hello world

'''
from flask import Flask, request
from fbmq import Page
import pyowm
import apiai
import json
import configparser


config = configparser.ConfigParser()
config.read('allegro.conf')
facebook_conf = config['Facbook']
PAGE_ACCESS_TOKEN = facebook_conf['PAGE_ACCESS_TOKEN']
VERIFY_TOKEN = facebook_conf['VERIFY_TOKEN']
CLIENT_ACCESS_TOKEN = facebook_conf['CLIENT_ACCESS_TOKEN']
owm_conf = config['OpenWeather']
OWM_TOKEN = owm_conf['OWM_TOKEN']

app = Flask(__name__)

page = Page(PAGE_ACCESS_TOKEN)
ai = apiai.ApiAI(CLIENT_ACCESS_TOKEN)

@app.route('/webhook', methods=['POST'])
def webhook():
    payload = request.get_data(as_text=True)
    print(payload)
    page.handle_webhook(payload)
    return "ok"


@page.handle_message
def message_handler(event):
    """:type event: fbmq.Event"""
    sender_id = event.sender_id
    message = event.message_text
    response = parse_user_message(message)
    page.send(sender_id, "%s" % response)


@page.after_send
def after_send(payload, response):
    """:type payload: fbmq.Payload"""
    print("complete")


def parse_user_message(user_message):
    '''
    Send the message to API AI which invokes an intent
    and sends the response accordingly
    The bot response is appened with weaher data fetched from
    open weather map client
    '''

    request = ai.text_request()
    request.query = user_message

    response = json.loads(request.getresponse().read().decode('utf-8'))
    responseStatus = response['status']['code']
    if (responseStatus == 200):

        print("API AI response", response['result']['fulfillment']['speech'])
        try:
            #Using open weather map client to fetch the weather report
            weather_report = ''

            input_city = response['result']['parameters']['geo-city']
            print("City ", input_city)

            owm = pyowm.OWM(OWM_TOKEN)  # You MUST provide a valid API key
            forecast = owm.daily_forecast(input_city)
            observation = owm.weather_at_place(input_city)
            w = observation.get_weather()
            print(w)
            print(w.get_wind())
            print(w.get_humidity())
            max_temp = str(w.get_temperature('celsius')['temp_max'])
            min_temp = str(w.get_temperature('celsius')['temp_min'])
            current_temp = str(w.get_temperature('celsius')['temp'])
            wind_speed = str(w.get_wind()['speed'])
            humidity = str(w.get_humidity())

            weather_report = 'max temp: ' + max_temp + ' min temp: ' + min_temp + ' current temp: ' + current_temp + ' wind speed :' + wind_speed + ' humidity ' + humidity + '%'
            print("Weather report ", weather_report)

            return (response['result']['fulfillment']['speech'] + weather_report)
        except:
            return (response['result']['fulfillment']['speech'])

    else:
        return ("Sorry, I couldn't understand that question")


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True, threaded=True)
