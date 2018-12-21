import requests
import json
from config import constants
from graphql_helper import GraphQLHelper

API_KEY = constants['SPORTSMONK_API_KEY']
season_id = "12950"    # ucl
# season_id = "12945"  # europa
# season_id = "12962"  # epl


graphql_helper = GraphQLHelper()
pos = {1: "G", 2: "D", 3: "M", 4: "F"}
url = "https://soccer.sportmonks.com/api/v2.0/standings/season/{SEASON_ID}?api_token={API_KEY}"\
        .format(SEASON_ID=season_id, API_KEY=API_KEY)
resp = requests.get(url)
data = json.loads(resp.text)["data"]
objects = []
for group in data:
    for team in group["standings"]["data"]:
        print team["team_id"]
        url = "https://soccer.sportmonks.com/api/v2.0/squad/season/{SEASON_ID}/team/{TEAM_ID}?api_token={API_KEY}" \
              "&include=player,position".format(SEASON_ID=season_id, TEAM_ID=team["team_id"], API_KEY=API_KEY)
        resp = requests.get(url)
        all_players = json.loads(resp.text)["data"]
        players = []
        for player in all_players:
            try:
                position = player["position"]["data"]["name"]
            except:
                continue
            player_obj = {
                "id": player["player_id"],
                "position": player["position"]["data"]["name"],
                "number": player["number"],
                "name": player["player"]["data"]["common_name"],
                "image_path": player["player"]["data"]["image_path"],
                "nationality": player["player"]["data"]["nationality"],
            }
            players.append(player_obj)
        resp = requests.get("https://soccer.sportmonks.com/api/v2.0/teams/" + str(team["team_id"]) +
                            "?api_token=" + API_KEY + "&include=country,squad,coach,venue,stats")
        team_data = json.loads(resp.text)["data"]
        team_obj = {
            "name": team_data["name"],
            "code": team_data["short_code"],
            "logo": team_data["logo_path"],
            "id": team["team_id"],
            "players": {"data": players, "on_conflict": {"constraint": "players_pkey"}}
        }
        objects.append(team_obj)

result = graphql_helper.upsert("teams", objects, "id")