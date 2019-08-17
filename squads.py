import requests
import json

from models import Squad, Player

POSITION_DICT = {
    "D": "Defender",
    "M": "Midfielder",
    "F": "Attacker",
    "G": "Defender"
}
url = "https://footballapi.pulselive.com/football/teams?page=0&pageSize=100&altIds=true&compSeasons=274"
resp = requests.get(url)
data = json.loads(resp.content)['content']
teams = []
players = []

for team in data:
    team_id = int(team['id'])
    url = f"https://footballapi.pulselive.com/football/teams/{team_id}/compseasons/274/staff?compSeasons=274&altIds=true&page=0&type=player"
    resp = requests.get(url)
    all_players = json.loads(resp.content)['players']

    for player in all_players:
        try:
            obj = {
                "id": "pulse_" + str(player["id"]),
                "name": player["name"]["display"],
                "number": player["info"]["shirtNum"] if "shirtNum" in player["info"] else 0,
                "position": POSITION_DICT[player['info']['position']],
                "image_path": None,
                "nationality": player["nationalTeam"]["country"],
                "team_id": "pulse_" + str(team_id)
            }
        except:
            continue
        players.append(obj)
    Player.insert_many(players).execute()
    team_obj = {
        "id": "pulse_" + str(int(team["id"])),
        "name": team["name"],
        "code": team["club"]['abbr'],
        "logo": None,
        "kit_path": None,
    }
    teams.append(team_obj)

Squad.insert_many(teams).execute()