import json
import requests

from db_utils import DbUtils
from config import constants


class Pulse:
    def __init__(self, fixture_id):
        self.fixture_id = fixture_id
        self.fixture_url = f"https://footballapi.pulselive.com/football/fixtures/{self.fixture_id}"
        self.events_url = f"https://footballapi.pulselive.com/football/fixtures/{self.fixture_id}/textstream/EN" \
                          "?pageSize=200&sort=desc"
        self.id_append_constant = "pulse_"
        self.point_events_dict = {
            "goal": "goal",
            "yellow card": "yellow card",
            "red card": "red card",
            "penalty miss": "penalty miss", #TODO: get pen miss type, change key
            "own goal": "own goal"
            # "attempt saved": "save"
        }

        self.player_id_to_name_dict = {}
        self.localteam_player_ids, self.visitorteam_player_ids = [], []
        self.localteam_gk_id, self.visitortem_gk_id = None, None

        self.fixtures_resp = self.get_match_resp(self.fixture_url)
        self.starting_xi = self.get_lineups(is_starting=True, status='active')
        self.subs = self.get_lineups(is_starting=False, status='inactive')
        DbUtils.set_starting_lineup(self.starting_xi + self.subs)
        self.events = self.get_all_events()
        for event in self.events:
            if event['type'] in self.point_events_dict.keys():
                self.process_point_event(event, event["playerIds"])

    def get_match_resp(self, url):
        resp = requests.get(url)
        return json.loads(resp.content)

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

    def get_all_events(self):
        events = json.loads(requests.get(self.events_url).content)
        return events['events']['content']

    def process_point_event(self, event, player_ids):
        DbUtils.set_event({
            "id": int(event["id"]),
            "player_id": self.id_append_constant + str(player_ids[0]),
            "fixture_id": self.id_append_constant + str(self.fixture_id),
            "minute": int(event["time"]["label"].split(" ")[0]),
            "type": self.point_events_dict[event["type"]],
            "points": constants["POINTS_DICT"][self.point_events_dict[event["type"]]]
        })
        if len(player_ids) > 1: #assist is the only case
            DbUtils.set_event({
                "id": int(event["id"]),
                "player_id": self.id_append_constant + str(player_ids[1]),
                "fixture_id": self.id_append_constant + str(self.fixture_id),
                "minute": int(event["time"]["label"].split(" ")[0]),
                "type": "assist",
                "points": constants["POINTS_DICT"]["assist"]
            })
