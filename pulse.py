import datetime
import logging
import os
import sys
import time
import traceback

import db_utils
from config import constants
from utils import init_logging, send_error_mail, get_pulse_response, calculate_proper_duration

GAME_START_STATUS = "L"
MATCH_END_MINUTE = 90


class Pulse:
    def __init__(self, fixture_id, game_status):
        self.fixture_id = fixture_id
        self.id_append_constant = "pulse_"
        self.clean_up_fixture()
        self.fixture_url = f"https://footballapi.pulselive.com/football/fixtures/{self.fixture_id}"
        self.events_url = f"https://footballapi.pulselive.com/football/fixtures/{self.fixture_id}/textstream/EN" \
                          "?pageSize=200&sort=desc"

        self.non_point_events_dict = {
            "end 14": "game over",
            "end 1": "half time",
            "end 2": "second half end",
            "substitution": "substitution"
        }
        self.point_events_dict = {
            "goal": "goal",
            "yellow card": "yellow card",
            "red card": "red card",
            "penalty miss": "penalty miss", #TODO: get pen miss type, change key
            "own goal": "own goal",
            "attempt saved": "save"
        }
        self.position_dict = {
            "G": "Goalkeeper",
            "D": "Defender",
            "M": "Midfielder",
            "F": "Attacker",  # TODO: get pen miss type, change key
        }

        self.player_id_to_name_dict = {}
        self.fixtures_resp = get_pulse_response(self.fixture_url)
        self.localteam_id, self.visitorteam_id = self.fixtures_resp['teamLists'][0]['teamId'], \
                                                 self.fixtures_resp['teamLists'][1]['teamId']
        self.localteam_player_ids, self.visitorteam_player_ids = [], []
        self.localteam_goal_minutes, self.visitorteam_goal_minutes = [], []
        self.localteam_gk_id, self.visitorteam_gk_id = None, None
        self.localteam_score, self.visitorteam_score = None, None

        self.starting_xi = self.get_lineups(is_starting=True, status='active')
        self.subs = self.get_lineups(is_starting=False, status='inactive')
        db_utils.set_starting_lineup(self.starting_xi + self.subs)

        if game_status == "live":
            while True:
                self.fixtures_resp = get_pulse_response(self.fixture_url)
                if self.fixtures_resp['status'] == GAME_START_STATUS:
                    logging.info(f"{self.fixture_id}: Game started")
                    db_utils.set_game_started(self.id_append_constant + str(self.fixture_id))
                    break
                else:
                    sleep_seconds = 60
                    logging.info(f"{self.fixture_id}: Game not started. Sleeping for {sleep_seconds} seconds")
                    time.sleep(sleep_seconds)
            self.check_for_events()
        else:
            self.events = get_pulse_response(self.events_url)['events']['content']
            for event in self.events:
                if event['type'] in self.point_events_dict.keys():
                    self.process_point_event(event, event["playerIds"])
            self.process_expired_user_picks(2 * MATCH_END_MINUTE + 1)

    def clean_up_fixture(self):
        db_utils.delete_lineup(self.id_append_constant + str(self.fixture_id))
        db_utils.delete_events(self.id_append_constant + str(self.fixture_id))
        db_utils.reset_user_picks(self.id_append_constant + str(self.fixture_id))

    def get_lineups(self, is_starting, status):
        lineup = []
        for team in self.fixtures_resp['teamLists']:
            for player in team['lineup' if is_starting else 'substitutes']:
                self.player_id_to_name_dict[player['id']] = player['name']['display']
                lineup.append({
                    "player_id": self.id_append_constant + str(player['id']),
                    "fixture_id": self.id_append_constant + str(self.fixture_id),
                    "team_id": self.id_append_constant + str(team['teamId']),
                    "position": player['matchPosition'],
                    "status": status
                })
                if team['teamId'] == self.localteam_id:
                    self.localteam_player_ids.append(player['id'])
                    if player['matchPosition'] == 'G' and is_starting:
                        self.localteam_gk_id = self.id_append_constant + str(player['id'])
                else:
                    self.visitorteam_player_ids.append(player['id'])
                    if player['matchPosition'] == 'G' and is_starting:
                        self.visitorteam_gk_id= self.id_append_constant + str(player['id'])
        return lineup

    def process_point_event(self, event, player_ids):
        team_id = self.localteam_id if player_ids[0] in self.localteam_player_ids else self.visitorteam_id
        player_id = self.id_append_constant + str(player_ids[0])
        minute = int(event["time"]["label"].split(" ")[0])
        points = constants["POINTS_DICT"][self.point_events_dict[event["type"]]]
        if self.point_events_dict[event["type"]] == "save":
            player_id = self.localteam_gk_id if team_id == self.visitorteam_id else self.visitorteam_gk_id
            team_id = self.visitorteam_id if player_ids[0] in self.localteam_player_ids else self.localteam_id
        is_success = db_utils.set_event({
            "id": int(event["id"]),
            "player_id": player_id,
            "fixture_id": self.id_append_constant + str(self.fixture_id),
            "team_id": self.id_append_constant + str(team_id),
            "minute": minute,
            "type": self.point_events_dict[event["type"]],
            "points": points
        })
        if not is_success:
            return
        logging.info(f"{event['id']}: {event['time']['label']}' "
                     f"{event['type']} - {self.player_id_to_name_dict[player_ids[0]]} ({points})")
        if event["type"] == "goal":
            if team_id == self.localteam_id:
                self.localteam_goal_minutes.append(minute)
            else:
                self.visitorteam_goal_minutes.append(minute)

            if len(player_ids) > 1:
                logging.info(f"{self.fixture_id}: assist - {self.player_id_to_name_dict[player_ids[1]]} ({constants['POINTS_DICT']['assist']})")
                db_utils.set_event({
                    "id": int(str(event["id"]) + "22"),  # random string added to prevent unique key error
                    "player_id": self.id_append_constant + str(player_ids[1]),
                    "fixture_id": self.id_append_constant + str(self.fixture_id),
                    "team_id": self.id_append_constant + str(team_id),
                    "minute": minute,
                    "type": "assist",
                    "points": constants["POINTS_DICT"]["assist"]
                })

    def process_non_point_event(self, event, player_ids):
        if event["type"] == "substitution":
            db_utils.set_substitution(self.id_append_constant + str(player_ids[0]),
                                      self.id_append_constant + str(player_ids[1]),
                                      self.id_append_constant + str(self.fixture_id))
            logging.info(f"{self.fixture_id}: Substitution - "
                         f"In: {self.player_id_to_name_dict[player_ids[0]]}"
                         f"Out: {self.player_id_to_name_dict[player_ids[1]]}")

        elif event["type"] == "end 1":
            logging.info(f"{self.fixture_id}: Half Time - Sleeping for 2 mins")
            time.sleep(60*2)

        elif event["type"] == "end 14":
            logging.info(f"{self.fixture_id}: Game Over")
            self.process_expired_user_picks(2 * MATCH_END_MINUTE + 1)
            db_utils.set_game_over(self.id_append_constant + str(self.fixture_id))
            sys.exit()

    def check_for_events(self):
        current_events_count = 0
        current_minute = 0
        while True:
            resp = get_pulse_response(self.events_url + "&ts=" + str(int(datetime.datetime.now().timestamp())))
            fixture_resp = get_pulse_response(self.fixture_url + "?ts=" + str(int(datetime.datetime.now().timestamp())))

            if " " in resp['fixture']['clock']['label']:  # eg 45 +2' - ignoring stoppage time
                current_minute_event = int(resp['fixture']['clock']['label'].split(" ")[0])
            else:  # eg 43'
                current_minute_event = int(resp['fixture']['clock']['label'].split("'")[0])

            if " " in fixture_resp['clock']['label']:  # eg 45 +2' - ignoring stoppage time
                current_minute_fixture = int(fixture_resp['clock']['label'].split(" ")[0])
            else:  # eg 43'
                current_minute_fixture = int(fixture_resp['clock']['label'].split("'")[0])

            current_minute = max(current_minute_event, current_minute_fixture, current_minute)
            self.localteam_score, self.visitorteam_score = resp['fixture']['teams'][0]['score'], \
                                                           resp['fixture']['teams'][1]['score']
            logging.info(f"{self.fixture_id}: Minute {current_minute}'")
            db_utils.set_current_fixture_state(current_minute,
                                               self.localteam_score,
                                               self.visitorteam_score,
                                               self.id_append_constant + str(self.fixture_id))
            events = resp['events']['content']
            new_events_count = len(events) - current_events_count
            for i in range(new_events_count):
                latest_event = events[i]
                if latest_event['type'] in self.point_events_dict.keys():
                    self.process_point_event(latest_event, latest_event["playerIds"])
                elif latest_event['type'] in self.non_point_events_dict.keys():
                    self.process_non_point_event(latest_event,
                                                 latest_event["playerIds"] if "playerIds" in latest_event else None)
            current_events_count = len(events)
            self.process_expired_user_picks(current_minute)
            time.sleep(60)

    def process_expired_user_picks(self, current_minute):
        to_be_expired = db_utils.get_to_be_expired(self.id_append_constant + self.fixture_id, current_minute)
        for row in to_be_expired:
            goal_minutes = self.visitorteam_goal_minutes if row.is_local_team else self.localteam_goal_minutes
            goals_conceded = 0
            for goal_minute in goal_minutes:
                if row.minute_of_buy <= goal_minute <= row.minute_of_expiry:
                    goals_conceded += 1
            player_id = int(row.player_id[len(self.id_append_constant):])
            if goals_conceded == 0:
                duration = min(MATCH_END_MINUTE, row.minute_of_expiry) - row.minute_of_buy
                if duration < 15:
                    continue
                duration = calculate_proper_duration(duration)
                points = constants["POINTS_DICT"][self.position_dict[row.player_position]][f"{duration}_min_no_goal"]
                logging.info(f"{self.fixture_id}: clean sheet - {self.player_id_to_name_dict[player_id]} ({points}) {duration} {row.player_position}")
            else:
                points = constants["POINTS_DICT"][self.position_dict[row.player_position]]["concede_goal"] * goals_conceded
                logging.info(f"{self.fixture_id}: {goals_conceded} goals conceded - {self.player_id_to_name_dict[player_id]} ({points}) {row.player_position}")
            db_utils.update_defensive_points(
                row.id,
                points
            )
        db_utils.set_expiry(self.id_append_constant + self.fixture_id, current_minute)


if __name__ == '__main__':
    try:
        init_logging(logging.INFO, filename=os.path.expanduser('~/logs/pulse.log'))
        Pulse(sys.argv[1], sys.argv[2])
    except Exception as e:
        logging.info(traceback.format_exc())
        send_error_mail(constants['NOTIF_MAIL'], traceback.format_exc())
