import os
import requests
import json
import datetime
import logging
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from config import constants
from utils import initLogging

API_KEY = constants['SPORTSMONK_API_KEY']
EPL_ID = 8
cred = credentials.Certificate(os.path.expanduser('~/matchday-firebase-firebase-adminsdk-83hhc-40b0ae1594.json'))
firebase_admin.initialize_app(cred)
db = firestore.Client()



if __name__ == '__main__':
    initLogging(logging.INFO, filename=os.path.expanduser('~/logs/matches.log'))
    tomorrow_date = str(datetime.date.today() + datetime.timedelta(days=1))
    logging.info("Matches for " + tomorrow_date)
    url = "https://soccer.sportmonks.com/api/v2.0/fixtures/date/{DATE}?" \
          "api_token=1SAjp0SrVOW9zgGST7ueE8XbQ5KCGopDefTwRTaDu0RvXLmGOmRYHJsBXQNc&include=" \
          "localTeam,visitorTeam,venue,stage,round,league,season,group".format(DATE=tomorrow_date)
    resp = requests.get(url)
    matches = json.loads(resp.text)["data"]
    for match in matches:
        if match['league_id'] != EPL_ID:
            continue
        doc_ref = db.document('matches/' + str(match["id"]))
        obj = {
            "id": match["id"],
            "localteam": {
                "id": match["localteam_id"],
                "name": match["localTeam"]["data"]["name"],
                "code": match["localTeam"]["data"]["short_code"],
                "icon": match["localTeam"]["data"]["logo_path"],
            },
            "visitorteam": {
                "id": match["visitorteam_id"],
                "name": match["visitorTeam"]["data"]["name"],
                "code": match["visitorTeam"]["data"]["short_code"],
                "icon": match["visitorTeam"]["data"]["logo_path"],
            },
            "competition": match["league"]["data"]["name"],
            "round": match["stage"]["data"]["name"],
            "stadium": match["venue"]["data"]["name"],
            "timestamp": match["time"]["starting_at"]["timestamp"] * 1000
        }
        doc_ref.set(obj)
        logging.info(str(match["id"]) + " : " + obj['localteam']['name'] + " v " + obj['visitorteam']['name'])
