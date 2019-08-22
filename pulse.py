import json
import logging
import os
import requests
import sys
import time
import traceback

from db_utils import DbUtils
from config import constants
from utils import init_logging, send_error_mail

GAME_START_STATUS = "L"


class Pulse:
    def __init__(self, fixture_id):

        self.fixture_id = fixture_id
        self.fixture_url = f"https://footballapi.pulselive.com/football/fixtures/{self.fixture_id}"
        self.events_url = f"https://footballapi.pulselive.com/football/fixtures/{self.fixture_id}/textstream/EN" \
                          "?pageSize=200&sort=desc"

        self.id_append_constant = "pulse_"
        self.non_point_events_dict = {
            "game over": "end 14",
            "half time": "end 1",
            "full time": "end 2",
            "substitution": "substitution"
        }
        self.point_events_dict = {
            "goal": "goal",
            "yellow card": "yellow card",
            "red card": "red card",
            "penalty miss": "penalty miss", #TODO: get pen miss type, change key
            "own goal": "own goal"
            # "attempt saved": "save" #TODO: changes to get saves data
        }

        self.player_id_to_name_dict = {}
        self.localteam_player_ids, self.visitorteam_player_ids = [], []
        self.localteam_gk_id, self.visitortem_gk_id = None, None

        while True:
            self.fixtures_resp = self.get_api_response_dict(self.fixture_url)
            if self.fixtures_resp['status'] == GAME_START_STATUS:
                DbUtils.set_game_started(self.id_append_constant + str(self.fixture_id))
                break
            else:
                time.sleep(300)

        self.starting_xi = self.get_lineups(is_starting=True, status='active')
        self.subs = self.get_lineups(is_starting=False, status='inactive')

        # DbUtils.set_starting_lineup(self.starting_xi + self.subs)
        self.check_for_events()
        # self.events = self.get_api_response_dict(self.events_url)['events']['content']
        # for event in self.events:
        #     if event['type'] in self.point_events_dict.keys():
        #         self.process_point_event(event, event["playerIds"])

    def get_lineups(self, is_starting, status):
        lineup = []
        for team in self.fixtures_resp['teamLists']:
            for player in team['lineup' if is_starting else 'substitutes']:
                self.player_id_to_name_dict[player['id']] = player['name']['display']
                lineup.append({
                    "player_id": self.id_append_constant + str(player['id']),
                    "fixture_id": self.id_append_constant + str(self.fixture_id),
                    "team_id": self.id_append_constant + str(team['teamId']),
                    "status": status
                })
        return lineup

    def process_point_event(self, event, player_ids):
        logging.info(f"{self.fixture_id}: {event['type']} - {self.player_id_to_name_dict[player_ids[0]]}")
        DbUtils.set_event({
            "id": int(event["id"]),
            "player_id": self.id_append_constant + str(player_ids[0]),
            "fixture_id": self.id_append_constant + str(self.fixture_id),
            "minute": int(event["time"]["label"].split(" ")[0]),
            "type": self.point_events_dict[event["type"]],
            "points": constants["POINTS_DICT"][self.point_events_dict[event["type"]]]
        })
        if len(player_ids) > 1:  # assist is the only case
            logging.info(f"{self.fixture_id}: assist - {self.player_id_to_name_dict[player_ids[1]]}")
            DbUtils.set_event({
                "id": int(event["id"]),
                "player_id": self.id_append_constant + str(player_ids[1]),
                "fixture_id": self.id_append_constant + str(self.fixture_id),
                "minute": int(event["time"]["label"].split(" ")[0]),
                "type": "assist",
                "points": constants["POINTS_DICT"]["assist"]
            })

    def process_non_point_event(self, event, player_ids):
        if event["type"] == self.non_point_events_dict["substitution"]:
            DbUtils.set_substitution(self.id_append_constant + str(self.fixture_id),
                                     self.id_append_constant + str(player_ids[0]),
                                     self.id_append_constant + str(player_ids[1]))
            logging.info(f"{self.fixture_id}: Substitution - "
                         f"In: {self.player_id_to_name_dict[player_ids[0]]}"
                         f"Out: {self.player_id_to_name_dict[player_ids[1]]}")

        elif event["type"] == self.non_point_events_dict["half time"]:
            logging.info(f"{self.fixture_id}: Half Time - Sleeping for 13 mins")
            time.sleep(60*13)

        elif event["type"] == self.non_point_events_dict["game over"]:
            logging.info(f"{self.fixture_id}: Game Over")
            DbUtils.set_game_over(self.id_append_constant + str(self.fixture_id))
            sys.exit()

    def check_for_events(self):
        current_events_count = 0
        while True:
            resp = self.get_api_response_dict(self.events_url)
            if " " in resp['fixture']['clock']['label']:  # eg 45 +2' - ignoring stoppage time
                current_minute = resp['fixture']['clock']['label'].split(" ")[0]
            else:  # eg 43'
                current_minute = resp['fixture']['clock']['label'].split("'")[0]
            logging.info(f"{self.fixture_id}: Minute {current_minute}'")
            DbUtils.set_current_time(int(current_minute), self.id_append_constant + str(self.fixture_id))
            events = resp['events']['content']
            new_events_count = len(events) - current_events_count
            i = 0
            while i < new_events_count:
                latest_event = events[i]
                if latest_event['type'] in self.point_events_dict.keys():
                    self.process_point_event(latest_event, latest_event["playerIds"])
                elif latest_event['type'] in self.non_point_events_dict.keys():
                    self.process_non_point_event(latest_event, latest_event["playerIds"])
                i = i + 1
            current_events_count = len(events)
            time.sleep(60)

    @staticmethod
    def get_api_response_dict(url):
        resp = requests.get(url)
        return json.loads(resp.content)


if __name__ == '__main__':
    try:
        init_logging(logging.INFO, filename=os.path.expanduser('~/logs/pulse.log'))
        Pulse(46624)
    except Exception as e:
        logging.info(traceback.format_exc())
        send_error_mail(constants['NOTIF_MAIL'], traceback.format_exc())