import os
import json
import subprocess
import requests
import logging
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from config import constants
from utils import init_logging

API_KEY = constants['SPORTSMONK_API_KEY']
cred = credentials.Certificate(os.path.expanduser('~/matchday-firebase-firebase-adminsdk-83hhc-40b0ae1594.json'))
firebase_admin.initialize_app(cred)
db = firestore.Client()



if __name__ == '__main__':
    init_logging(logging.INFO, filename=os.path.expanduser('~/logs/start_match.log'))
    url = "https://soccer.sportmonks.com/api/v2.0/livescores/now?api_token=" + API_KEY + "&include=localTeam,visitorTeam"
    resp = requests.get(url)
    matches = json.loads(resp.text)["data"]
    for match in matches:
        if match['league_id'] in constants['LEAGUES']:
            match_doc = db.document('matches/' + str(match['id'])).get()
            if match_doc._data['started'] is False:
                db.document('matches/' + str(match['id'])).update({"started":True})
                logging.info('Starting match ' + str(match['id']) + ' ' + str(match['localTeam']['data']['name'])
                             + ' v ' + match['visitorTeam']['data']['name'])
                cmd = "python {PATH}main.py {MATCH_ID} live".format(PATH=constants['ROOT_PATH'], MATCH_ID=match['id'])
                subprocess.Popen(cmd, shell=True, stdin=None, stdout=None, stderr=None, close_fds=True)