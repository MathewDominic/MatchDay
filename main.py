import sys
import os
import logging
import json
import time
import requests
import traceback
import random

from utils import init_logging, to_ascii, send_error_mail
from config import constants
from graphql_helper import GraphQLHelper

API_KEY = constants['SPORTSMONK_API_KEY']
EVENTS = constants['EVENTS']
POINTS_DICT = constants['POINTS_DICT']
POSITION_DICT = constants['POSITION_DICT']


class MatchDay:
    def __init__(self, match_id):
        self.match_id = match_id
        self.graphql_helper = GraphQLHelper()
        self.id_to_player_dict = {}
        self.player_stats = {}
        self.player_points = {}
        self.current_minute = 0
        self.local_active_players, self.visitor_active_players = [], []
        self.local_concede_minutes, self.visitor_concede_minutes = [], []
        self.starting_xi = []
        # loop to handle case when api is not returning all starting players on first call
        while True:
            match_url = "https://soccer.sportmonks.com/api/v2.0/fixtures/" + self.match_id + "?api_token=" + API_KEY + \
                        "&include=localTeam,visitorTeam,substitutions,goals,cards,other,lineup,bench,stats,comments," \
                        "highlights,events"

            resp = requests.get(match_url)
            data = json.loads(resp.text)["data"]
            self.starting_xi = data["lineup"]["data"]
            if len(self.starting_xi) == 22:
                break
            time.sleep(60)

        self.init_match_details()
        self.local_team_id = int(data["localTeam"]["data"]["id"])
        self.visitor_team_id = int(data["visitorTeam"]["data"]["id"])
        self.subs = data["bench"]["data"]
        self.all_events = data["events"]["data"]
        self.populate_starting_players()
        self.populate_bench_players()
        self.add_bots()

    def init_match_details(self):
        self.graphql_helper.update(table="fixtures",
                                 equals_obj="{id: {_eq: " + str(match_id) + "}}",
                                 set_obj="{current_minute: 0,current_second: 0}",
                                 return_column="id")
    def populate_starting_players(self):
        player_lineup = []
        for player in self.starting_xi:
            self.id_to_player_dict[player["player_id"]] = {"name": player["player_name"], "position" : player["position"]}
            team_id = int(player["team_id"])
            player_lineup_obj = {
                "player_id": player['player_id'],
                "fixture_id": int(self.match_id),
                "status": "active",
                "team_id": team_id
            }
            player_lineup.append(player_lineup_obj)

            if team_id == int(self.local_team_id):
                self.local_active_players.append(player['player_id'])
            else:
                self.visitor_active_players.append(player['player_id'])
        self.graphql_helper.upsert("lineups", player_lineup, "player_id")

    def populate_bench_players(self):
        for player in self.subs:
            self.id_to_player_dict[player["player_id"]] = {"name": player["player_name"], "position": player["position"]}

    def add_bots(self):
        bots = ["bot1", "bot2"]
        bot_user_teams = []
        for bot_id, bot in enumerate(bots):
            players = []
            while len(players) < 10:
                if len(players) < 5:
                    player = random.choice(self.local_active_players)
                else:
                    player = random.choice(self.visitor_active_players)
                if player not in players:
                    players.append(player)
            logging.info(str(self.match_id) + bot + str(players))
            for player in players:
                user_team_obj = {
                    "active": True,
                    "duration": 60,
                    "is_local": True,
                    "fixture_id": int(self.match_id),
                    "player_id": player,
                    "points": 0,
                    "price": 20,
                    "minute_of_buy": 0,
                    "minute_of_expiry": 60,
                    "user_id": bot_id + 1,
                    "player_position": unicode(POSITION_DICT[self.id_to_player_dict[player]['position']]),
                    "is_local_team": player in self.local_active_players,
                }
                bot_user_teams.append(user_team_obj)
        self.graphql_helper.upsert("user_teams", bot_user_teams, "id")

    def process_substitution(self, event, active_players):
        logging.info(str(self.match_id) + "subs" + ' ' + str(event["player_id"]) + ' ' + str(event["related_player_id"]))
        # remove subbed off def
        if event["related_player_id"] in active_players:
            logging.info(str(self.match_id) + 'remove' + ' ' + str(event["related_player_id"]) + ' ' + to_ascii(event["related_player_name"]))
            active_players.remove(event["related_player_id"])

        # add subbed on def
        logging.info(str(self.match_id) + 'add' + ' ' + str(event["player_id"]) + ' ' + to_ascii(event["player_name"]))
        active_players.append(event["player_id"])

        return active_players

    def get_points_for_goal(self, position):
        # if position == 'F':
        #     return POINTS_DICT["striker_score"]
        # elif position == 'M':
        #     return POINTS_DICT["midfielder_score"]
        # else:
        #     return POINTS_DICT["defender_score"]
        return POINTS_DICT["score"]

    def process_point(self, player_id, event_desc, event, points):
        if player_id is not None:
            event_dict = {
                "id": event['id'],
                "description": unicode(event_desc, "utf-8"),
                "points": points,
                "minute": event["minute"],
                "fixture_id": int(self.match_id),
                "player_id": int(player_id),
            }
            if player_id not in self.player_stats:
                self.player_stats[player_id] = []
            self.player_stats[player_id].append(event_dict)
            if player_id not in self.player_points:
                self.player_points[player_id] = points
            else:
                self.player_points[player_id] = self.player_points[player_id] + points
            self.graphql_helper.upsert("events", [event_dict], "id")
            self.update_user_teams(event_dict)

    def update_user_teams(self, event_dict):
        pass
        update_condition = "{" \
                                "fixture_id: {_eq: " + self.match_id + "}," + \
                                "player_id: {_eq: " + str(event_dict['player_id']) + "}," + \
                                "minute_of_buy: {_lte: " + str(int(event_dict['minute'])) + "}," \
                                "minute_of_expiry: {_gte: " + str(int(event_dict['minute'])) + "}" \
                            "}"
        user_teams_updated = self.graphql_helper.update(table="user_teams",
                                                        equals_obj=update_condition,
                                                        inc_obj="{points: " + str(event_dict['points']) + "}",
                                                        return_column="id")
        pass

    def get_comments(self, last_comment_minute, data):
        comments = data["comments"]["data"]
        if len(comments) == 0:
            return
        last_comment = comments[len(comments) - 1]
        if int(last_comment["minute"]) > int(last_comment_minute):
            logging.info(str(self.match_id) + "comment" + ' ' + str(last_comment["minute"]) + ' ' + to_ascii(last_comment["comment"]))
        last_comment_minute = last_comment["minute"]
        return last_comment_minute

    def check_for_event(self, events):
        for event in events:
            if len(self.all_events) == 0:
                logging.info(str(self.match_id) + 'New event')
                self.process_event(event)
            else:
                new_event = True
                for old_event in self.all_events:
                    if event["id"] == old_event["id"]:
                        new_event = False
                        if event["minute"] != old_event["minute"]:
                            logging.info(str(self.match_id) + 'Event minute changed' + ' ' + str(event))
                        if event["player_id"] != old_event["player_id"]:
                            logging.info(str(self.match_id) + 'Event player_id changed' + ' ' + str(event))
                            if event["type"] == EVENTS["goal"]:
                                logging.info(str(self.match_id) + 'Goal' + ' ' + str(event["player_id"]) + ' ' + to_ascii(event["player_name"]))
                                position = self.id_to_player_dict[event['player_id']]['position']
                                points = self.get_points_for_goal(position)
                                self.process_point(event["player_id"], "goal", event, points)
                            elif event["type"] == EVENTS["own goal"]:
                                logging.info(str(self.match_id) + 'Own goal' + ' ' + str(event["player_id"]) + ' ' + to_ascii(event["player_name"]))
                                self.process_point(event["player_id"], "own goal", event, POINTS_DICT['own_goal'])
                        if event["related_player_id"] != old_event["related_player_id"]:
                            logging.info(str(self.match_id) + 'Event related_player_id changed' + ' ' + str(event))
                            self.process_point(event["related_player_id"], "assist", event, POINTS_DICT["assist"])
                if new_event is True:
                    logging.info(str(self.match_id) + 'New event')
                    self.process_event(event)

    def process_event(self, event):
        logging.info(str(self.match_id) + "Event at minute" + ' ' + str(event.get("minute", -1)))
        if event["type"] == EVENTS["goal"] or event["type"] == "penalty":
            logging.info(str(self.match_id) + 'Goal' + ' ' + str(event["player_id"]) + ' ' + to_ascii(event["player_name"]))

            if int(event["team_id"]) == self.local_team_id:
                self.visitor_concede_minutes.append(int(event["minute"]))
            else:
                self.local_concede_minutes.append(int(event["minute"]))

            if event['player_id'] is None:
                return
            position = self.id_to_player_dict[event['player_id']]['position']
            points = self.get_points_for_goal(position)
            self.process_point(event["player_id"], "goal", event, points)

            logging.info(str(self.match_id) + 'Assist ' + str(event["related_player_id"]) + ' ' + to_ascii(event["related_player_name"]))
            self.process_point(event["related_player_id"], "assist", event, POINTS_DICT["assist"])

        elif event["type"] == EVENTS["penalty miss"]:
            logging.info(str(self.match_id) + 'Penalty miss' + ' ' + str(event["player_id"]) + ' ' + to_ascii(event["player_name"]))
            self.process_point(event["player_id"], "penalty miss", event, POINTS_DICT['penalty_miss'])

        elif event["type"] == EVENTS["own goal"]:
            logging.info(str(self.match_id) + 'Own goal' + ' ' + str(event["player_id"]) + ' ' + to_ascii(event["player_name"]))
            self.process_point(event["player_id"], "own goal", event, POINTS_DICT['own_goal'])

            logging.info(str(self.match_id) + 'Assist' + ' ' + str(event["related_player_id"]) + ' ' + to_ascii(event["related_player_name"]))
            self.process_point(event["related_player_id"], "assist", event, POINTS_DICT["assist"])

        elif event["type"] == EVENTS["substitution"]:
            if int(event["team_id"]) == int(self.local_team_id):
                self.local_active_players = self.process_substitution(event, self.local_active_players)
            else:
                self.visitor_active_players = self.process_substitution(event, self.visitor_active_players, )
            player_lineup_obj = {
                "player_id": event['player_id'],
                "fixture_id": int(self.match_id),
                "status": "active",
                "team_id": event['team_id']
            }
            self.graphql_helper.upsert("lineups", [player_lineup_obj], "player_id")

            update_condition = "{" \
                                    "fixture_id: {_eq: " + self.match_id + "}," + \
                                    "player_id: {_eq: " + str(event['related_player_id']) + "}," + \
                                    "team_id: {_eq: " + str(event['team_id']) + "}" \
                                "}"
            self.graphql_helper.update(table="lineups",
                                       equals_obj=update_condition,
                                       set_obj='{status: "inactive"}',
                                       return_column="player_id")

        elif event["type"] == EVENTS["yellow card"]:
            logging.info(str(self.match_id) + 'Yellow card' + ' ' + str(event["player_id"]) + ' ' + to_ascii(event["player_name"]))
            self.process_point(event["player_id"], "yellow card", event, POINTS_DICT['yellow_card'])

        elif event["type"] == EVENTS["red card"]:
            logging.info(str(self.match_id) + 'Red card' + ' ' + str(event["player_id"]) + ' ' + to_ascii(event["player_name"]))
            self.process_point(event["player_id"], "red card", event, POINTS_DICT['red_card'])

        else:
            logging.info(str(self.match_id) + "no event in dict" + ' ' + str(event["type"]))

    def check_for_expiry(self, minute):
        update_condition =  "{" \
                                "fixture_id: {_eq: " + self.match_id  + "}," + \
                                "active: {_eq: true},"  + \
                                "minute_of_expiry: {_lte: "  + str(int(minute - 2)) + "}" \
                            "}"
        players_expired = self.graphql_helper.update(table="user_teams",
                                                     equals_obj=update_condition,
                                                     set_obj="{active: false}",
                                                     return_column="id, player_position, minute_of_buy, minute_of_expiry, duration, is_local_team")
        for player in players_expired:
            player_position = player['player_position']
            if player_position == 'Attacker':
                continue
            concede_minutes = md.local_concede_minutes if player['is_local_team'] is True else md.visitor_concede_minutes
            goals_conceded = 0
            for concede_minute in concede_minutes:
                if player['minute_of_buy'] <= concede_minute <= player['minute_of_expiry']:
                    goals_conceded = 1
                    break
            if goals_conceded == 0:
                no_goal_points = POINTS_DICT[player_position][str(player['duration']) + "_min_no_goal"]
                update_condition = "{" \
                                        "id: {_eq: " + str(player['id']) + "}" + \
                                    "}"
                user_teams_updated = self.graphql_helper.update(table="user_teams",
                                                                equals_obj=update_condition,
                                                                inc_obj="{points: " + str(no_goal_points) + "}",
                                                                return_column="id")


if __name__ == '__main__':
    try:
        init_logging(logging.INFO, filename=os.path.expanduser('~/logs/main.log'))
        match_id = sys.argv[1]
        md = MatchDay(match_id)
        live_match_update = True if sys.argv[2] == "live" else False
        current_minute = 0
        if live_match_update:
            while True:
                match_url = "https://soccer.sportmonks.com/api/v2.0/fixtures/" + match_id + "?api_token=" + API_KEY + \
                            "&include=events,stats,comments"
                resp = requests.get(match_url)
                try:
                    data = json.loads(resp.text)["data"]
                except:
                    time.sleep(10)
                    continue
                time_obj = data["time"]
                events = data["events"]["data"]
                if time_obj.get("status") != 'LIVE' and time_obj.get("status") != 'ET':
                    if time_obj.get("status") == 'FT':
                        md.check_for_expiry(250)
                        logging.info(str(match_id) + 'Game over')
                        md.graphql_helper.update(table="fixtures",
                                                 equals_obj="{id: {_eq: " + str(match_id) + "}}",
                                                 set_obj="{has_ended: true}",
                                                 return_column="id")
                        break
                    logging.info(str(match_id) + 'not live, sleep for 60')
                    time.sleep(60)
                    continue
                else:
                    time_obj = data["time"]
                    if time_obj["minute"] > current_minute:
                        md.check_for_expiry(time_obj["minute"])
                    current_minute = time_obj["minute"]
                    md.check_for_event(events)
                    md.graphql_helper.update(table="fixtures",
                                             equals_obj="{id: {_eq: " + str(match_id) + "}}",
                                             set_obj="{current_minute: " + time_obj["minute"] + ",current_second" + time_obj["second"] + "}",
                                             return_column="id")
                    time.sleep(10)
                    md.all_events = events
                    continue

        else:
            match_url = "https://soccer.sportmonks.com/api/v2.0/fixtures/" + match_id + "?api_token=" + API_KEY + \
                        "&include=events:order(minute|asc),stats,comments"
            resp = requests.get(match_url)
            data = json.loads(resp.text)["data"]
            events = data["events"]["data"]
            events = sorted(data["events"]["data"], key=lambda event: event['minute'])
            for event in events:
                if event["minute"] > md.current_minute:
                    md.check_for_expiry(event["minute"])
                md.current_minute = event["minute"]
                md.graphql_helper.update(table="fixtures",
                                         equals_obj="{id: {_eq: " + str(match_id) + "}}",
                                         set_obj="{current_minute: " + str(md.current_minute) + ",current_second:" + str(0) + "}",
                                         return_column="id")
                md.process_event(event)
            md.check_for_expiry(250)
    except Exception as e:
        logging.info(str(match_id) + traceback.format_exc())
        send_error_mail(constants['NOTIF_MAIL'], traceback.format_exc())











