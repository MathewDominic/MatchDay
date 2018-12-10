import sys
import os
import logging
import json
import time
import requests
import firebase_admin
import traceback
import random

from firebase_admin import firestore,credentials
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
        cred = credentials.Certificate(os.path.expanduser('~/matchday-firebase-firebase-adminsdk-83hhc-40b0ae1594.json'))
        firebase_admin.initialize_app(cred)
        self.db = firestore.Client()
        self.graphql_helper = GraphQLHelper()
        self.match_doc_ref= self.db.document('matches/' + match_id)
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

        if data["time"]["status"] == "NS":
            self.match_doc_ref.update({"current_minute": 0, "current_second": 0})

        self.local_team_id = int(data["localTeam"]["data"]["id"])
        self.visitor_team_id = int(data["visitorTeam"]["data"]["id"])
        self.subs = data["bench"]["data"]
        self.all_events = data["events"]["data"]
        self.populate_starting_players()
        self.populate_bench_players()
        self.add_bots()

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
        self.graphql_helper.upsert("lineups", "player_id", player_lineup)

    def populate_bench_players(self):
        for player in self.subs:
            self.id_to_player_dict[player["player_id"]] = {"name": player["player_name"], "position": player["position"]}

    def add_bots(self):
        bots = ["bot1", "bot2"]
        for bot in bots:
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
                    "duration": 90,
                    "isLocal": True,
                    "matchId": int(self.match_id),
                    "player_id": player,
                    "points": 0,
                    "userId": unicode(bot),
                    "player_position": unicode(POSITION_DICT[self.id_to_player_dict[player]['position']]),
                    "is_local_team_player": player in self.local_active_players
                }
                self.db.document('userTeams/' + bot + str(player)).set(user_team_obj)

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
                "id": event["id"],
                "desc": unicode(event_desc, "utf-8"),
                "points": points,
                "minute": event["minute"],
                "match_id": int(self.match_id),
                "player_id": int(player_id),
                "player_name": self.id_to_player_dict[int(player_id)]["name"],
                "player_position": self.id_to_player_dict[int(player_id)]["position"],
                "timestamp": int(time.time() * 100)
            }
            if player_id not in self.player_stats:
                self.player_stats[player_id] = []
            self.player_stats[player_id].append(event_dict)
            if player_id not in self.player_points:
                self.player_points[player_id] = points
            else:
                self.player_points[player_id] = self.player_points[player_id] + points
            try:
                self.db.document('player_stats/' + str(self.match_id) + '_' + str(player_id) + '/events/' + str(event["id"])).update(event_dict)
            except:
                self.db.document('player_stats/' + str(self.match_id) + '_' + str(player_id)).set(
                    {
                        "total_points": self.player_points[player_id],
                        "player_details": self.id_to_player_dict[player_id],
                        "match_id": int(self.match_id)
                    })
                self.db.document('player_stats/' + str(self.match_id) + '_' + str(player_id) + '/events/' + str(event["id"])).set(event_dict)

            self.db.document('player_stats/' + str(self.match_id) + '_' + str(player_id)).update({"total_points": self.player_points[player_id]})
            self.update_user_teams(event, player_id, event_dict, points)

    def update_user_teams(self, event, player_id, event_dict, points):
        user_teams_to_update = list((self.db.collection('userTeams')
                                     .where(u'player_id', u'==', int(player_id))
                                     .where(u'matchId', u'==', int(self.match_id)))
                                     # .where(u'active', u'==', True)
                                    # .where(u'minuteOfExpiry', u'<=', int(event["minute"] + 30))
                                    # .where(u'minuteOfExpiry', u'>=', int(event["minute"])))
                                    .get())
        for team in user_teams_to_update:
            if 'minuteOfExpiry' not in team._data:
                continue
            if team._data['minuteOfBuy'] <= int(event["minute"]) <= team._data['minuteOfExpiry']:
                doc = team._reference
                self.db.document('userTeams/' + doc._path[1] + '/events/' + str(event["id"])).set(event_dict)
                self.db.document('userTeams/' + doc._path[1]).update({'points': team._data['points'] + points})
                self.update_leaderboard(team._data['userId'], points)

    def update_leaderboard(self, user_id, points):
        leaderboard_entry = list(self.db.collection('leaderboard').where(u'user_id', u'==', unicode(user_id))
                                                  .where(u'match_id', u'==', unicode(self.match_id))
                                                  .get())
        if len(leaderboard_entry) > 0:
            self.db.document('leaderboard/' + str(user_id) + '_' + str(self.match_id))\
                .update({"points": leaderboard_entry[0]._data['points'] + points})
        else:
            user_name = "null"
            user = list(self.db.collection('users').where(u'id', u'==', unicode(user_id)).get())
            if len(user) > 0:
                if user[0]._data['id'] is not None:
                    user_name = user[0]._data['name']
            leaderboard_obj = {
                "match_id": unicode(self.match_id),
                "user_id": unicode(user_id),
                "user_name": unicode(user_name),
                "points": points
            }
            self.db.document('leaderboard/' + str(user_id) + "_" + str(self.match_id)).set(leaderboard_obj)

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
                self.match_doc_ref.update({"visitorteam_concede_minutes": self.visitor_concede_minutes})
            else:
                self.local_concede_minutes.append(int(event["minute"]))
                self.match_doc_ref.update({"localteam_concede_minutes": self.local_concede_minutes})

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
                self.db.document('active_players/' + self.match_id).update({"localteam_active_players": self.local_active_players})
            else:
                self.visitor_active_players = self.process_substitution(event, self.visitor_active_players, )
                self.db.document('active_players/' + self.match_id).update({"visitorteam_active_players": self.visitor_active_players})

        elif event["type"] == EVENTS["yellow card"]:
            logging.info(str(self.match_id) + 'Yellow card' + ' ' + str(event["player_id"]) + ' ' + to_ascii(event["player_name"]))
            self.process_point(event["player_id"], "yellow card", event, POINTS_DICT['yellow_card'])

        elif event["type"] == EVENTS["red card"]:
            logging.info(str(self.match_id) + 'Red card' + ' ' + str(event["player_id"]) + ' ' + to_ascii(event["player_name"]))
            self.process_point(event["player_id"], "red card", event, POINTS_DICT['red_card'])

        else:
            logging.info(str(self.match_id) + "no event in dict" + ' ' + str(event["type"]))

    def check_for_expiry(self, minute):
        players_expired = list((self.db.collection('userTeams')
                                     # .where(u'minuteOfExpiry', u'<', int(minute) - 2)
                                     .where(u'matchId', u'==', int(self.match_id))
                                     .where(u'active', u'==', True))
                                    # .where(u'minuteOfExpiry', u'<=', int(event["minute"] + 30))
                                    # .where(u'minuteOfExpiry', u'>=', int(event["minute"])))
                                    .get())
        for player in players_expired:
            player_position = player._data['player_position']
            if 'minuteOfExpiry' not in player._data:
                continue
            if (player._data['minuteOfExpiry'] + 2) < minute:
                doc = player._reference
                self.db.document('userTeams/' + doc._path[1]).update({'active':False})
                if player_position == 'Attacker':
                    continue
                concede_minutes = md.local_concede_minutes if player._data['is_local_team_player'] is True else md.visitor_concede_minutes
                goals_conceded = 0
                for concede_minute in concede_minutes:
                    if player._data['minuteOfBuy'] <= concede_minute <= player._data['minuteOfExpiry']:
                        goals_conceded = goals_conceded + 1
                # if goals_conceded == 0:
                #     duration = int(player._data['duration'])
                #     event = {  # dummy event dict
                #         "id": str(minute) + str(duration),
                #         "minute": player._data['minuteOfExpiry'],
                #     }
                #     event_dict = {
                #         "id": unicode(str(minute) + str(duration)),
                #         "minute": minute,
                #         "desc": unicode(str(duration) + "_minute_no_concede"),
                #         "points": POINTS_DICT[player_position][str(int(duration)) + "_min_no_goal"]
                #     }
                #     self.db.document('userTeams/' + str(player.id) + '/events/' + str(event["id"])).set(event_dict)
                #     self.db.document('userTeams/' + str(player.id)).update({'points': player._data['points'] + event_dict["points"]})
                #     self.update_leaderboard(str(player._data['userId']), event_dict["points"])

                duration = int(player._data['duration'])
                event = {  # dummy event dict
                    "id": str(minute) + str(duration),
                    "minute": player._data['minuteOfExpiry'],
                }
                event_dict = {
                    "id": unicode(str(minute) + str(duration)),
                    "minute": minute,
                }
                if goals_conceded == 0:
                    event_dict["desc"] = unicode(str(duration) + "_minute_no_concede")
                    event_dict["points"] = POINTS_DICT[player_position][str(int(duration)) + "_min_no_goal"]
                else:
                    event_dict["desc"] = unicode(str(duration) + "_minute_" + str(goals_conceded) + "_concede")
                    event_dict["points"] = goals_conceded * POINTS_DICT[player_position]["concede_goal"]
                self.db.document('userTeams/' + str(player.id) + '/events/' + str(event["id"])).set(event_dict)
                self.db.document('userTeams/' + str(player.id)).update(
                    {'points': player._data['points'] + event_dict["points"]})
                self.update_leaderboard(str(player._data['userId']), event_dict["points"])


                # elif goals_conceded >= 2:
                #     self.update_user_teams(player._data['player_id'], {"desc": str(minute) + "more_than_one_goal_conceded"}, POINTS_DICT["90_min_no_goal"])

    # if no_goal:
    #     self.process_no_goal_minute(self.visitor_active_players)
    #     self.process_no_goal_minute(self.local_active_players)
    # else:
    #     visitor_concede = False
    #     local_concede = False
    #     for goal_event in goal_events:
    #         if int(goal_event["team_id"]) == self.local_team_id:
    #             visitor_concede = True
    #         else:
    #             local_concede = True
    #         self.process_goal_minute(goal_event)
    #     if visitor_concede is False:
    #         self.process_no_goal_minute(self.visitor_active_players)
    #     if local_concede is False:
    #         self.process_no_goal_minute(self.local_active_players)
    # def update_player_points(self, all_matches, player_with_point, player_point):
    #     for matches in all_matches.each():
    #         match_details = matches.item[1]
    #         for user_team in match_details["user_teams"]:
    #             user_team_dict = match_details["user_teams"][user_team]
    #             player_ids_in_team = user_team_dict.keys()
    #             if player_with_point in player_ids_in_team and user_team_dict[player_with_point]["is_active"] is True:
    #                 current_active_points  = db.child("matches/" + self.match_id + "/user_teams" + "/" + user_team + "/" + "player_2" + "/active_points").get().pyres
    #                 data = {"matches/" + self.match_id + "/user_teams" + "/" + user_team + "/" + player_with_point + "/active_points": current_active_points + player_point}
    #                 db.update(data)
    #
    #                 current_total_points = db.child("matches/" + self.match_id + "/user_teams" + "/" + user_team + "/" + "player_2" + "/total_points").get().pyres
    #                 data = {"matches/" + self.match_id + "/user_teams" + "/" + user_team + "/" + player_with_point + "/total_points": current_total_points + player_point}
    #                 db.update(data)


if __name__ == '__main__':
    try:
        init_logging(logging.INFO, filename=os.path.expanduser('~/logs/main.log'))
        match_id = sys.argv[1]
        md = MatchDay(match_id)
        live_match_update = True if sys.argv[2] == "live" else False
        current_minute = 0
        # md.check_for_expiry(100)
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
                    md.match_doc_ref.update({"current_minute": time_obj["minute"], "current_second": time_obj["second"]})
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
                md.match_doc_ref.update({"current_minute": md.current_minute, "current_second": 0})
                md.process_event(event)
            md.check_for_expiry(250)
    except Exception as e:
        logging.info(str(match_id) + traceback.format_exc())
        send_error_mail(constants['NOTIF_MAIL'], traceback.format_exc())











