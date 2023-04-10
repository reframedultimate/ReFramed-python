from reframed import Replay
from datetime import datetime


rfr = Replay("data/2023-04-04_23-59-52 -  - Free (WR1) -  (Byleth) vs  (Diddy Kong) - Game 1 (0-0) - Town and City.rfr")

# Get player tags
player_tags = [
    rfr["playerinfo"][0]["tag"],
    rfr["playerinfo"][1]["tag"]
]

# Get player fighter names
player_fighter_ids = [
    rfr["playerinfo"][0]["fighterid"],
    rfr["playerinfo"][1]["fighterid"]
]
player_fighters = [
    rfr["mappinginfo"]["fighterid"][player_fighter_ids[0]],
    rfr["mappinginfo"]["fighterid"][player_fighter_ids[1]],
]

# Get winner
winner = player_tags[rfr["gameinfo"]["winner"]]

# Timestamps are in milli-seconds, but python expects seconds
time_started = datetime.fromtimestamp(rfr["gameinfo"]["timestampstart"] / 1000)
time_ended = datetime.fromtimestamp(rfr["gameinfo"]["timestampend"] / 1000)

# Stage
stage = rfr["mappinginfo"]["stageid"][rfr["gameinfo"]["stageid"]]

print("Replay details")
print("==============")
print(f"{player_tags[0]} ({player_fighters[0]}) vs {player_tags[1]} ({player_fighters[1]})")
print(f"Start time: {time_started}")
print(f"End time: {time_ended}")
print(f"Stage: {stage}")
print(f"Winner: {winner}")
