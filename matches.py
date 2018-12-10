import os
import requests
import json
import datetime
import logging
import traceback
from config import constants
from utils import init_logging, send_error_mail
from graphql_helper import GraphQLHelper

API_KEY = constants['SPORTSMONK_API_KEY']



if __name__ == '__main__':
    try:
        graphql_helper = GraphQLHelper()
        init_logging(logging.INFO, filename=os.path.expanduser('~/logs/matches.log'))
        tomorrow_date = str(datetime.date.today() + datetime.timedelta(days=1))
        logging.info("Matches for " + tomorrow_date)
        url = "https://soccer.sportmonks.com/api/v2.0/fixtures/date/{DATE}?" \
              "api_token={API_KEY}&include=" \
              "localTeam,visitorTeam,venue,stage,round,league,season,group".format(DATE=tomorrow_date,API_KEY=API_KEY)
        resp = requests.get(url)
        matches = json.loads(resp.text)["data"]
        objects = []
        for match in matches:
            if match['league_id'] in constants['LEAGUES']:
                obj = {
                    "id": match["id"],
                    "starts_by": match["time"]["starting_at"]["timestamp"] * 1000,
                    "has_started": False,
                    "has_ended": False,
                    "localteam_id": match["localteam_id"],
                    "visitorteam_id": match["visitorteam_id"],
                    "competition_id": match["league"]["data"]["id"],
                    "round": match["stage"]["data"]["name"],
                    "stadium": match["venue"]["data"]["name"],
                }
                objects.append(obj)
        graphql_helper.upsert("fixtures", "id", objects)
    except Exception as e:
        logging.info(traceback.format_exc())
        send_error_mail(constants['NOTIF_MAIL'], traceback.format_exc())
