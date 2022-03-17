import numpy as np
import matplotlib.pyplot as plt
from reframed import Replay

rfr = Replay("data/2022-03-17 - Friendlies - Player 1 (Lucina) vs Player 2 (Pikachu) Game 1.rfr")


# Get state information of first player on first frame
state = rfr["playerstates"][0][0]

print("First frame")
print("===========")
print(f"frame: {state['frame']}")
print(f"posx: {state['posx']}")
print(f"posy: {state['posy']}")
print(f"damage: {state['damage']}")
print(f"hitstun: {state['hitstun']}")
print(f"shield: {state['shield']}")
print(f"status: {state['status']} ({rfr['mappinginfo']['fighterstatus']['base'][state['status']][0]})")
print(f"motion: {state['motion']} (hash40 value of current animation)")
print(f"hit_status: {state['hit_status']} ({rfr['mappinginfo']['hitstatus'][state['hit_status']]})")
print(f"stocks: {state['stocks']}")
print(f"attack_connected: {state['attack_connected']}")
print(f"facing_direction: {state['facing_direction']}")
