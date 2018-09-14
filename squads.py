from google.cloud import storage
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import requests
import json
cred = credentials.Certificate('/Users/mathew/Downloads/matchday-firebase-firebase-adminsdk-83hhc-40b0ae1594.json')
firebase_admin.initialize_app(cred)
storage_client = storage.Client()
db = firestore.Client()


pos = {1:"G", 2:"D", 3:"M", 4:"F"}
url = "https://soccer.sportmonks.com/api/v2.0/standings/season/12962?api_token=1SAjp0SrVOW9zgGST7ueE8XbQ5KCGopDefTwRTaDu0RvXLmGOmRYHJsBXQNc"
resp = requests.get(url)
data = json.loads(resp.text)["data"]
for group in data:
    for team in group["standings"]["data"]:
        print team["team_id"]
        url = "https://soccer.sportmonks.com/api/v2.0/squad/season/12962/team/%s?api_token=1SAjp0SrVOW9zgGST7ueE8XbQ5KCGopDefTwRTaDu0RvXLmGOmRYHJsBXQNc&include=player,position" % team["team_id"]
        resp = requests.get(url)
        all_players = json.loads(resp.text)["data"]
        players = {}
        for player in all_players:
            try:
                position = player["position"]["data"]["name"]
            except:
                continue
            doc_ref = db.document('squads/' + str(team["team_id"]) + '/players/' + str(player["player_id"]))
            obj = {
                "player_id": player["player_id"],
                "position": player["position"]["data"]["name"],
                "number": player["number"],
                "injured": player["injured"],
                "minutes": player["minutes"],
                "appearences": player["appearences"],
                "lineups": player["lineups"],
                "substitute_in": player["substitute_in"],
                "substitute_out": player["substitute_out"],
                "substitutes_on_bench": player["substitutes_on_bench"],
                "goals": player["goals"],
                "assists": player["assists"],
                "yellowcards": player["yellowcards"],
                "yellowred": player["yellowred"],
                "redcards": player["redcards"],
                "name": player["player"]["data"]["common_name"],
                "image_path": player["player"]["data"]["image_path"],
                "nationality": player["player"]["data"]["nationality"],
                "birthdate": player["player"]["data"]["birthdate"],
                "height": player["player"]["data"]["height"],
                "weight": player["player"]["data"]["weight"]
            }
            players[str(player["player_id"])] = obj
            # doc_ref.set(obj)
        resp = requests.get("https://soccer.sportmonks.com/api/v2.0/teams/" + str(team["team_id"]) + "?api_token=1SAjp0SrVOW9zgGST7ueE8XbQ5KCGopDefTwRTaDu0RvXLmGOmRYHJsBXQNc&include=country,squad,coach,venue,stats")
        logo = json.loads(resp.text)["data"]["logo_path"]
        doc_ref = db.document('squads/' + str(team["team_id"]))
        doc_ref.set({"name": team["team_name"], "players": players, "logo":logo})