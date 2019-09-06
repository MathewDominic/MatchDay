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


SCORECARD_DICT = {
    "num_of_fours": "4s",
    "num_of_sixes": "6s",
    "num_of_runs": "r",
    "num_of_overs": "o",
    "num_of_wickets": "w",
    "num_of_no_balls": "n",
    "num_of_wides": "wd",
    "num_of_maidens": "m"
}

EVENTS_TO_POINT_DICT = {
    "four": "4s",
    "six": "6s",
    "run": "r",
    "wicket": "w",
    "no_balls": "n",
    "wide": "wd",
}

DUMMY_BATSMAN_DICT = {
    SCORECARD_DICT["num_of_fours"]: 0,
    SCORECARD_DICT["num_of_sixes"]: 0,
    SCORECARD_DICT["num_of_runs"]: 0,
}

DUMMY_BOWLER_DICT = {
    # SCORECARD_DICT["num_of_overs"]: 0,
    # SCORECARD_DICT["num_of_maidens"]: 0
    SCORECARD_DICT["num_of_wickets"]: 0,
    SCORECARD_DICT["num_of_no_balls"]: 0,
    SCORECARD_DICT["num_of_wides"]: 0
}


def check_event(current_dict, latest_dict, player_id, player_type, current_ball):
    stats = dict.keys(DUMMY_BATSMAN_DICT) if player_type == "batsman" else dict.keys(DUMMY_BOWLER_DICT)
    for stat in stats:
        if stat in current_dict and stat in latest_dict:
            if int(latest_dict[stat]) > int(current_dict[stat]):
                count = int(latest_dict[stat]) - int(current_dict[stat])
                process_event(stat, count, player_id, current_ball)
                # special case for wides and no balls. Decrementing one ball so as to process next ball
                if stat in (SCORECARD_DICT["num_of_wides"], SCORECARD_DICT["num_of_no_balls"]):
                    current_ball -= 0.1
    return current_ball


def process_event(stat, count, player_id, current_ball):
    if stat == SCORECARD_DICT["num_of_fours"]:
        print str(current_ball), player_id, "four"
    elif stat == SCORECARD_DICT["num_of_sixes"]:
        print str(current_ball), player_id, "six"
    elif stat == SCORECARD_DICT["num_of_runs"]:
        print str(current_ball), player_id, str(count) + " runs"
    elif stat == SCORECARD_DICT["num_of_wickets"]:
        print str(current_ball), player_id, "wicket"
    elif stat == SCORECARD_DICT["num_of_no_balls"]:
        print str(current_ball), player_id, "no ball"
    elif stat == SCORECARD_DICT["num_of_wides"]:
        print str(current_ball), player_id, "wide"
    else:
        print "Unknown event", stat


if __name__ == '__main__':
    match_id= '22507'
    points_by_ball_dict = {}
    current_scores_dict = {}
    url = "https://www.cricbuzz.com/match-api/{match_id}/commentary-full.json".format(match_id=match_id)
    resp = json.loads(requests.get(url).text)
    commentary = list(filter(lambda x: "o_no" in x, resp["comm_lines"]))
    commentary = sorted(commentary, key=lambda x: x['timestamp'])
    past_ball = 0.0
    for event in commentary:
        # print event["o_no"]
        current_ball = float(event["o_no"])
        if current_ball > past_ball:
            batsman_id = event['batsman'][0]['id']
            bowler_id = event['bowler'][0]['id']
            if batsman_id not in current_scores_dict:
                current_scores_dict[batsman_id] = event['batsman'][0]
                current_ball = check_event(DUMMY_BATSMAN_DICT, current_scores_dict[batsman_id], batsman_id, "batsman",
                                           current_ball)
            else:
                current_ball = check_event(current_scores_dict[batsman_id], event['batsman'][0], batsman_id, "batsman",
                                           current_ball)
                current_scores_dict[batsman_id] = event['batsman'][0]

            if bowler_id not in current_scores_dict:
                current_scores_dict[bowler_id] = event['bowler'][0]
                current_ball = check_event(DUMMY_BOWLER_DICT, current_scores_dict[bowler_id], bowler_id, "bowler",
                                           current_ball)
            else:
                current_ball = check_event(current_scores_dict[bowler_id], event['bowler'][0], bowler_id, "bowler",
                                           current_ball)
                current_scores_dict[bowler_id] = event['bowler'][0]
            past_ball = float(current_ball)


#TODO detect whos out
#TODO detect run outs
#TODO detect caught out catcher
