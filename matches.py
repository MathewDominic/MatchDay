import datetime
import json
import logging
import os
import requests
import traceback

import db_utils
from models import Fixture
from utils import init_logging, send_error_mail, get_pulse_response

if __name__ == '__main__':
    try:
        init_logging(logging.INFO, filename=os.path.expanduser('~/logs/matches.log'))
        tomorrow_date = datetime.date.today() + datetime.timedelta(days=0)
        logging.info("Matches for " + tomorrow_date.strftime("%d %b %Y"))
        url = "https://footballapi.pulselive.com/football/fixtures" \
              "?page=0&startDate={date}&comps={competition_id}".format(date=str(tomorrow_date), competition_id=1)
        resp = get_pulse_response(url)
        matches = resp['content']
        objects = []
        for match in matches:
            obj = {
                "id": "pulse_" + str(int(match["id"])),
                "has_started": False,
                "has_ended": False,
                "current_minute": 0,
                "current_second": 0,
                "localteam_score": 0,
                "visitorteam_score": 0,
                "round": "Gameweek " + str(int(match["gameweek"]["gameweek"])),
                "stadium": match["ground"]["name"],
                "competition_id": 1,
                "localteam_id": "pulse_" + str(int(match["teams"][0]["team"]["id"])),
                "visitorteam_id": "pulse_" + str(int(match["teams"][1]["team"]["id"])),
                "starts_by": int(match["kickoff"]["millis"]) / 1000,
            }
            objects.append(obj)
            logging.info(str(int(match["id"])) + " : " + match["teams"][0]["team"]["shortName"] + " v " + match["teams"][1]["team"]["shortName"])
        db_utils.insert_fixtures(objects)
    except Exception as e:
        logging.info(traceback.format_exc())
        # send_error_mail(constants['NOTIF_MAIL'], traceback.format_exc())