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
    sim.showNodes()  # Show nodeDB as seen by each node

    """ Broadcast Message from node 0 """
    fromNode = 0
    sim.sendBroadcast("Hi all", fromNode)

    """ Direct Message from node 1 to node 0 """
    # fromNode = 1
    # toNode = 0
    # sim.sendDM("Hi node 0", fromNode, toNode)

    """ Ping node 1 from node 0 """
    # fromNode = 0
    # toNode = 1
    # sim.sendPing(fromNode, toNode)

    """ Admin Message (setOwner) from node 0 to node 1 
        (First add shared admin channel.) """
    # for n in sim.nodes:
    #     n.addAdminChannel()     
    # fromNode = 0
    # toNode = 2
    # sim.sendFromTo(fromNode, toNode).setOwner(long_name="Test")  # can be any function in Node class

    time.sleep(30) # Wait until message are sent
    sim.closeNodes()
except KeyboardInterrupt:
    sim.closeNodes()

sim.graph.initRoutes()  # Visualize the route of messages sent 