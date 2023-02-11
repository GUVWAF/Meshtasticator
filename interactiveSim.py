""" Simulator for letting multiple instances of native programs 
    communicate via TCP as if they did via their LoRa chip. 
    Usage: python3 interactiveSim.py [nrNodes] [--p <full-path-to-program>] [--d] [--s]
    Use '--d' for Docker. Use '--s' to specify what should be send using this script.
"""
import time
from lib.common import *
from lib.interactive import *

sim = interactiveSim() # Start the simulator

if sim.script:  # Use '--s' as argument if you want to specify what you want to send here
    try:
        time.sleep(45)  # Wait until nodeInfo messages are sent
        sim.showNodes()  # Show nodeDB as seen by each node

        fromNode = 0  # Node from which a message will be send
        toNode = 1  # Node to whom a message will be send (if not a broadcast)

        """ Broadcast Message from node 0. """
        sim.sendBroadcast("Hi all", fromNode)

        """ Direct Message from node 0 to node 1. """
        # sim.sendDM("Hi node 0", fromNode, toNode)

        """ Ping node 1 from node 0. """
        # sim.sendPing(fromNode, toNode)

        """ Admin Message (setOwner) from node 0 to node 1.
            First you need to add a shared admin channel. """
        # for n in sim.nodes:
        #     n.addAdminChannel()  # or sim.getNodeById(n.nodeid).setURL(<'YOUR_URL'>)  
        # sim.sendFromTo(fromNode, toNode).setOwner(long_name="Test")  # can be any function in Node class

        """ Trace route from node 0 to node 1. 
            Result will be in the log of node 0. """
        # sim.traceRoute(fromNode, toNode)

        """ Send a position request from node 0 to node 1. """
        # sim.requestPosition(fromNode, toNode)

        time.sleep(15) # Wait until message are sent
        sim.graph.plotMetrics(sim.nodes) # Plot airtime metrics
        sim.graph.initRoutes(sim)  # Visualize the route of messages sent 
    except KeyboardInterrupt:
        sim.graph.plotMetrics(sim.nodes)
        sim.graph.initRoutes(sim)
else:  # Normal usage with commands
    CommandProcessor().cmdloop(sim)
