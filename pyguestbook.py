# PyGuestbook API written by Ash :3
# this turned into a bit more than a guestbook api   woops

from flask import json, Flask, jsonify, request, abort, render_template, make_response, Response
from markupsafe import escape
import csv
import time
import re

from base64 import b64encode

from werkzeug.exceptions import HTTPException

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from ashiecaptcha import CAPTCHA
import configparser
config = configparser.ConfigParser()
config.read('ashiecaptcha.ini')
CAPTCHA_CONFIG = {'SECRET_CAPTCHA_KEY':config['CAPTCHA_CONFIG']['SECRET_CAPTCHA_KEY'], 
    'METHOD': config['CAPTCHA_CONFIG']['METHOD'],
    'CAPTCHA_LENGTH': int(config['CAPTCHA_CONFIG']['CAPTCHA_LENGTH']),
    'CAPTCHA_DIGITS': config['CAPTCHA_CONFIG'].getboolean('CAPTCHA_DIGITS') }
CAPTCHA = CAPTCHA(config=CAPTCHA_CONFIG)

### App setup

app = Flask(__name__)
app = CAPTCHA.init_app(app)

# create ratelimiter :333
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["5 per day", "2 per minute"],
    storage_uri="memory://"
)

#vars or something
validEmail = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

# database file path
ashDbFile = 'ash-guestbook.csv'
zenDbFile = 'zen-guestbook.csv'

### Error routing

@app.errorhandler(HTTPException)
def handle_exception(e):
    """Return JSON instead of HTML for HTTP errors."""
    # start with the correct headers and status code from the error
    response = e.get_response()

    if e.description == "requesting challenges too fast.":
        response = make_response(render_template('captcha-error.html'), 429)
        return response
    # replace the body with JSON
    response.data = json.dumps({
        "code": e.code,
        "name": e.name,
        "description": e.description,
    })
    response.content_type = "application/json"
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

### Captcha routing and functions

# captcha page render
@app.route('/captcha/<string:db>', methods=['GET'])
@limiter.limit('1/second', methods=['GET'], error_message='requesting challenges too fast.')
def captcha(db):
    captcha = CAPTCHA.create()
    if db == "ashiecorner":
        response = make_response(render_template('captcha.html', captcha=captcha))
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET'
        return response
    elif db == "zencorner":
        response = make_response(render_template('captcha-zen.html', captcha=captcha))
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET'
        return response
    else:
        return abort(400, 'Invalid site entry for captcha.')

### Guestbook API routing and functions

# post a guestbook entry
@app.route('/guestbook/postEntry/<string:db>', methods=['POST'])
@limiter.limit('10/day', methods=['POST'], error_message='You have posted the max daily amount of guestbook entries (10). Please try again tommorow.')
def post_entry(db):
    #resolve which database to pull from
    dbFile = ''
    if db == "ashiecorner":
        dbFile = ashDbFile
    elif db == "zencorner":
        dbFile = zenDbFile
    else:
        return abort(400, 'Invalid database query.')
    
    # if there literally isnt any request info return bad request
    if not request.form:
        return abort(400, 'No form info provided.')
    
    # turn form request into dictionary
    gbEntry = dict(request.form)

    # get current time in epoch
    date_time = int(time.time())

    # lengths of entries
    nameL = len(gbEntry['name'])
    messageL = len(gbEntry['message'])
    emailL = len(gbEntry['email'])

    # escaped to prevent XSS attacks
    # translated to prevent database shitfuckery
    trans = {ord(i):None for i in ''}
    name = escape(gbEntry['name']).translate(trans)
    email = escape(gbEntry['email']).translate(trans)
    message = escape(gbEntry['message']).translate(trans)

    # if name or message is too short/long, or email too long return http 400
    if nameL < 1 or nameL > 35:
        return abort(400, 'Name missing/too long.')
    elif messageL < 1 or messageL > 140:
        return abort(400, 'Message missing/too long.')

    # if email exists, check if its valid lmao
    if emailL > 0 and not re.fullmatch(validEmail, email) or emailL > 140:
        return abort(400, 'Invalid email.')

    # verify captcha
    c_hash = request.form.get('captcha-hash')
    c_text = request.form.get('captcha-text')
    if CAPTCHA.verify(c_text, c_hash):
        with open(dbFile, mode='a', newline='') as csv_file:
            data = csv.writer(csv_file, delimiter='')
            if emailL > 0:
                data.writerow([name, b64encode(email.encode('utf-8')).decode('ascii'), message, date_time])
            else:
                data.writerow([name, '', message, date_time])
        okResp = Response(status=200)
        okResp.headers['Access-Control-Allow-Origin'] = '*'
        return okResp
    else:
        return abort(400, 'Invalid captcha.')

    

# get all guestbook entries (lol lmao)
@app.route('/guestbook/getEntries/<string:db>', methods=['GET'])
@limiter.limit('1/second', methods=['GET'], error_message='You are fetching guestbook entries too quickly.')
def get_entries(db):
    #resolve which database to pull from
    dbFile = ''
    if db == "ashiecorner":
        dbFile = ashDbFile
    elif db == "zencorner":
        dbFile = zenDbFile
    else:
        return abort(400, 'Invalid database query.')

    # read csv file
    with open(dbFile, mode='r') as csv_file:
        reader = csv.reader(csv_file, delimiter='')
        data = []
        for i, x in enumerate(reader):
            data.append(x)

        # reverse data list to give correct time order (top->bottom)
        data.reverse()

        response = jsonify(data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response

### Hitcounter API routing and functions

# register hit in database (ashiecorner)
@app.route('/hc/h/ashiecorner', methods=['POST'])
@limiter.limit('1/day', methods=['POST'], error_message='Cannot count more than 1 hit per day.')
def postHitA():
    with open('hitcounter.txt', mode='r+') as f:
        data = f.readline().split(',')
        data[1] = str(int(data[1]) + 1)
        
        final = ','.join(data)
        f.seek(0)
        f.write(final)

        okResp = Response(status=200)
        okResp.headers['Access-Control-Allow-Origin'] = '*'
        return okResp

# get hits from database (ashiecorner)
@app.route('/hc/gh/ashiecorner', methods=['GET'])
@limiter.limit('1/second', methods=['GET'], error_message='You are fetching hits too quickly.')
def getHitsA():
    with open('hitcounter.txt', mode='r', newline='') as f:
        data = f.readline().split(',')
        response = jsonify({'hits': data[1].strip()})
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET'
        return response

# register hit in database (zencorner)
@app.route('/hc/h/zencorner', methods=['POST'])
@limiter.limit('1/day', methods=['POST'], error_message='Cannot count more than 1 hit per day.')
def postHitZ():
    with open('hitcounter.txt', mode='r+') as f:
        data = f.readline().split(',')
        data[0] = str(int(data[0]) + 1)
        
        final = ','.join(data)
        f.seek(0)
        f.write(final)

        okResp = Response(status=200)
        okResp.headers['Access-Control-Allow-Origin'] = '*'
        return okResp

# get hits from database (zencorner)
@app.route('/hc/gh/zencorner', methods=['GET'])
@limiter.limit('1/second', methods=['GET'], error_message='You are fetching hits too quickly.')
def getHitsZ():
    with open('hitcounter.txt', mode='r', newline='') as f:
        data = f.readline().split(',')
        response = jsonify({'hits': data[0].strip()})
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET'
        return response

if __name__ == '__main__':
    app.run(host='0.0.0.0')
