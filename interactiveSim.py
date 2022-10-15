""" Simulator for letting multiple instances of native programs 
    communicate via TCP as if they did via their LoRa chip. 
    Usage: python3 interactiveSim.py [nrNodes] [--p <full-path-to-program>]
    Specify what you want to send in the 'try' clause. 
"""
import time
from lib.common import *
from lib.interactive import *

sim = interactiveSim() # Start the simulator

try:
    time.sleep(40)  # Wait until nodeInfo messages are sent
    text = "Hi there, how are you doing?"

    # Broadcast Message from node 0
    fromNode = 0
    sim.sendBroadcast(text, fromNode)

    # Direct Message from node 1 to node 0
    # fromNode = 1
    # toNode = 0
    # sendDM(text, fromNode, toNode)

    # Ping node 1 from node 0
    # fromNode = 0
    # toNode = 1
    # sendPing(fromNode, toNode)

    time.sleep(15) # Wait until message are sent
    sim.closeNodes()
except KeyboardInterrupt:
    sim.closeNodes()

sim.graph.initRoutes()  # Visualize the route of messages sent 