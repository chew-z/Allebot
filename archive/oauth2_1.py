'''
This is oauth2 autorization to Allegro REST API
Useless beside proof that it can be done
'''

from requests_oauthlib import OAuth2Session
from flask import Flask, request, redirect, session, url_for
from flask.json import jsonify
import os
import logging
import configparser
import requests

app = Flask(__name__)

config = configparser.ConfigParser()
config.read('allegro.conf')
allegro_conf = config['Allegro']

client_id = allegro_conf['CLIENT_ID']
client_secret = allegro_conf['CLIENT_SECRET']
authorization_base_url = allegro_conf['AUTHORIZATION_BASE_URL']
token_url = allegro_conf['TOKEN_URL']
api_key = allegro_conf['API_KEY']
redirect_uri = allegro_conf['REDIRECT_URI']


@app.route("/")
def hello():
    return "Hello World!"

@app.route("/login")
def login():
    """Step 1: User Authorization.

    Redirect the user/resource owner to the OAuth provider
    using an URL with a few key OAuth parameters.
    """
    allegro = OAuth2Session(client_id, redirect_uri=redirect_uri)
    authorization_url, state = allegro.authorization_url(authorization_base_url, Response_type='code')

    # State is used to prevent CSRF, keep this for later.
    session['oauth_state'] = state
    return redirect(authorization_url)


# Step 2: User authorization, this happens on the provider.

@app.route("/oauth2callback", methods=["GET", "POST"])
def callback():
    """ Step 3: Retrieving an access token.

    The user has been redirected back from the provider to your registered
    callback URL. With this redirection comes an authorization code included
    in the redirect URL. We will use that to obtain an access token.
    """

    code = request.args.get('code')
    logging.info("code = {}".format(code))

    payload = {
            'grant_type': 'authorization_code',
            'code': code,
            'api-key': api_key,
            'redirect_uri': redirect_uri
            }
    try:
        resp = requests.post('https://allegro.pl/auth/oauth/token', auth=(client_id, client_secret), data=payload)
        logging.info(resp.headers)
        token = resp.json()['access_token']
        logging.info("token = {}".format(token))
    except Exception as e:
        logging.error(e)
    return jsonify({"result": resp.json()})


if __name__ == "__main__":
    # This allows us to use a plain HTTP callback
    # os.environ['DEBUG'] = "1"
    # os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
    try:
        os.remove('oauth2.log')
    except BaseException:
        pass
    logging.basicConfig(filename='oauth2.log', level=logging.DEBUG,
                        format=FORMAT, datefmt='%a, %d %b %Y %H:%M:%S',)
    logging.info('--- oauth2.py logging started ---.')

    app.secret_key = os.urandom(24)
    app.run(debug=True, port=8080)

    logging.info('--- oauth2.py logging finished ---.')

