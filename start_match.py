import os
import json
import subprocess
import requests
import logging
from config import constants
from utils import init_logging, send_error_mail

API_KEY = constants['SPORTSMONK_API_KEY']
from graphql_helper import GraphQLHelper



if __name__ == '__main__':
    graphql_helper = GraphQLHelper()
    init_logging(logging.INFO, filename=os.path.expanduser('~/logs/start_match.log'))
    url = "https://soccer.sportmonks.com/api/v2.0/livescores/now?api_token=" + API_KEY + "&include=localTeam,visitorTeam"
    resp = requests.get(url)
    matches = json.loads(resp.text)["data"]
    for match in matches:
        if match['league_id'] in constants['LEAGUES']:
            match = graphql_helper.select("fixtures",
                                          "{id: {_eq: " + str(match['id']) + "}}",
                                          "{}",
                                          "id,has_started")
            if len(match['data']['fixtures']) == 0:
                send_error_mail(constants['NOTIF_MAIL'], "No match")
            elif match['data']['fixtures'][0]['has_started'] is False:
                graphql_helper.update("fixtures",
                                      "{id: {_eq: " + str(match['id']) + "}}",
                                      "{has_started: true}",
                                      "id")
                logging.info('Starting match ' + str(match['id']) + ' ' + str(match['localTeam']['data']['name'])
                             + ' v ' + match['visitorTeam']['data']['name'])
                cmd = "python {PATH} {MATCH_ID} live".format(PATH=os.path.join(os.getcwdu(), "main.py"), MATCH_ID=match['id'])
                subprocess.Popen(cmd, shell=True, stdin=None, stdout=None, stderr=None, close_fds=True)