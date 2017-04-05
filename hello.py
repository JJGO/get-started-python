from cloudant import Cloudant
from flask import Flask, render_template, request, jsonify
import atexit
import cf_deployment_tracker
import os
import json

from watson_developer_cloud import LanguageTranslatorV2

# Emit Bluemix deployment event
cf_deployment_tracker.track()

app = Flask(__name__)

db_name = 'mydb_translate'
client = None
db = None
translator = None

if 'VCAP_SERVICES' in os.environ:
    vcap = json.loads(os.getenv('VCAP_SERVICES'))
    print('Found VCAP_SERVICES')
    if 'cloudantNoSQLDB' in vcap:
        creds = vcap['cloudantNoSQLDB'][0]['credentials']
        user = creds['username']
        password = creds['password']
        url = 'https://' + creds['host']
        client = Cloudant(user, password, url=url, connect=True)
        db = client.create_database(db_name, throw_on_exists=False)

        creds = vcap['language_translator'][0]['credentials']
        user = creds['username']
        password = creds['password']
        # url = 'https://' + creds['url']
        url = creds['url']
        print(user, password, url)
        translator = LanguageTranslatorV2(username=user, password=password, url=url)

elif os.path.isfile('vcap-local.json'):
    with open('vcap-local.json') as f:
        vcap = json.load(f)
        print('Found local VCAP_SERVICES')
        if 'cloudantNoSQLDB' in vcap['services']:
            # cloudantNoSQLDB
            creds = vcap['services']['cloudantNoSQLDB'][0]['credentials']
            user = creds['username']
            password = creds['password']
            url = 'https://' + creds['host']
            client = Cloudant(user, password, url=url, connect=True)
            db = client.create_database(db_name, throw_on_exists=False)

        creds = vcap['services']['language_translator'][0]['credentials']
        user = creds['username']
        password = creds['password']
        url = creds['url']
        translator = LanguageTranslatorV2(username=user, password=password, url=url)


# On Bluemix, get the port number from the environment variable PORT
# When running this app on the local machine, default the port to 8080
port = int(os.getenv('PORT', 8080))


@app.route('/')
def home():
    return render_template('index.html')

# /* Endpoint to greet and add a new visitor to database.
# * Send a POST request to localhost:8080/api/visitors with body
# * {
# * 	"name": "Bob"
# * }
# */


@app.route('/api/visitors', methods=['GET'])
def get_visitor():
    if client:
        return jsonify(list(map(lambda doc: doc['name'], db)))
    else:
        print('No database')
        return jsonify([])

# /**
#  * Endpoint to get a JSON array of all the visitors in the database
#  * REST API example:
#  * <code>
#  * GET http://localhost:8080/api/visitors
#  * </code>
#  *
#  * Response:
#  * [ "Bob", "Jane" ]
#  * @return An array of all the visitor names
#  */
@app.route('/api/visitors', methods=['POST'])
def put_visitor():
    user = request.json['name']
    original = user
    # Translate
    test = user.startswith('__')
    if test:
        user = user.strip('_')
    user = translator.translate(user, source='es', target='en')

    if client:
        if not test:
            data = {'name': user}
            db.create_document(data)
        return 'La traduccion de {0} es {1}'.format(original, user)
    else:
        print('No database')
        return 'Buenos dias %s!' % user

@atexit.register
def shutdown():
    if client:
        client.disconnect()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port, debug=True)
