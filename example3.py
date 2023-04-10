import numpy as np
import matplotlib.pyplot as plt
from reframed import Replay

rfr = Replay("data/2023-04-04_23-59-52 -  - Free (WR1) -  (Byleth) vs  (Diddy Kong) - Game 1 (0-0) - Town and City.rfr")


def gen_distances():
    p1 = [(state["posx"], state["posy"]) for state in rfr["playerstates"][0]]
    p2 = [(state["posx"], state["posy"]) for state in rfr["playerstates"][1]]
    for p1, p2 in zip(p1, p2):
        dx = p1[0] - p2[0]
        dy = p2[1] - p2[1]
        dist = np.sqrt(dx**2 + dy**2)
        yield dist


# For every frame calculate the distance between player 1 and player 2 and put the result into an array
distances = np.array(list(gen_distances()))

# Plot histogram of distances
plt.hist(distances, bins=50)
plt.show()
