""" Simulator for letting multiple instances of native programs 
    communicate via TCP as if they did via their LoRa chip. 
    Usage: python3 interactiveSim.py [nrNodes] [--p <full-path-to-program>]
"""

import sys
import os
import time

from lib.common import *
from lib.phy import estimatePathLoss
from pubsub import pub
import meshtastic.tcp_interface
from meshtastic import mesh_pb2, admin_pb2, telemetry_pb2, remote_hardware_pb2

class interactiveNode(): 
    def __init__(self, nodes, nodeId, hwId, TCPPort, x=-1, y=-1):
        self.nodeid = nodeId
        self.x = x
        self.y = y
        self.hwId = hwId
        self.TCPPort = TCPPort 
        if self.x == -1 and self.y == -1:
            self.x, self.y = findRandomPosition(nodes)

    def addInterface(self, iface):
        self.iface = iface


class realPacket():
    def __init__(self, packet, id):
        self.packet = packet
        self.localId = id
        
    def setTxRxs(self, transmitter, receivers):
        self.transmitter = transmitter
        self.receivers = receivers

    def setRSSISNR(self, rssis, snrs):
        self.rssis = rssis
        self.snrs = snrs


def forwardPacket(iface, packet, rssi, snr): 
    data = packet["decoded"]["payload"]
    if getattr(data, "SerializeToString", None):
        data = data.SerializeToString()

    if len(data) > mesh_pb2.Constants.DATA_PAYLOAD_LEN:
        raise Exception("Data payload too big")

    if packet["decoded"]["portnum"] == "TEXT_MESSAGE_APP":
        meshPacket = mesh_pb2.MeshPacket()
    elif packet["decoded"]["portnum"] == "ROUTING_APP":
        meshPacket = mesh_pb2.Routing()
    elif packet["decoded"]["portnum"] == "NODEINFO_APP":
        meshPacket = mesh_pb2.NodeInfo()
    elif packet["decoded"]["portnum"] == "POSITION_APP":
        meshPacket = mesh_pb2.Position()
    elif packet["decoded"]["portnum"] == "USER_APP":
        meshPacket = mesh_pb2.User()  
    elif packet["decoded"]["portnum"] == "ADMIN_APP":
        meshPacket = admin_pb2.AdminMessage()
    elif packet["decoded"]["portnum"] == "TELEMETRY_APP":
        meshPacket = telemetry_pb2.Telemetry()
    elif packet["decoded"]["portnum"] == "REMOTE_HARDWARE_APP":
        meshPacket = remote_hardware_pb2.HardwareMessage()
    else:
        meshPacket = mesh_pb2.MeshPacket()

    meshPacket.decoded.payload = data
    meshPacket.decoded.portnum = 69
    meshPacket.to = packet["to"]
    setattr(meshPacket, "from", packet["from"])
    meshPacket.id = packet["id"]
    if "wantAck" in packet:
        meshPacket.want_ack = packet["wantAck"]
    if "hopLimit" in packet:
        meshPacket.hop_limit = packet["hopLimit"]
    if "requestId" in packet["decoded"]:
        meshPacket.decoded.request_id = packet["decoded"]["requestId"]
    if "wantResponse" in packet["decoded"]:
        meshPacket.decoded.want_response = packet["decoded"]["wantResponse"]
    meshPacket.rx_rssi = int(rssi) 
    meshPacket.rx_snr = int(snr)  
    toRadio = mesh_pb2.ToRadio()
    toRadio.packet.CopyFrom(meshPacket)
    iface._sendToRadio(toRadio)


def sendBroadcast(text, fromNode):
    nodes[fromNode].iface.sendText(text)


def sendDM(text, fromNode, toNode):
    nodes[fromNode].iface.sendText(text, destinationId=nodes[toNode].hwId, wantAck=True)


def onReceive(interface, packet): 
    global messageId
    if "requestId" in packet["decoded"]:
        # Packet with requestId is coupled to original message
        existingMsgId = next((m.localId for m in messages if m.packet["id"] == packet["decoded"]["requestId"]), None)
        if existingMsgId == None:
            print('Could not find requestId!\n')
        mId = existingMsgId
    else:
        existingMsgId = next((m.localId for m in messages if m.packet["id"] == packet["id"]), None)
        if existingMsgId != None:
            mId = existingMsgId
        else: 
            messageId += 1
            mId = messageId
    rP = realPacket(packet, mId)
    messages.append(rP)
    print("Node", interface.myInfo.my_node_num-HW_ID_OFFSET, "sent", packet["decoded"]["simulator"]["portnum"], "with id", mId, "over the air!")
    transmitter = next((n for n in nodes if n.TCPPort == interface.portNumber), None)
    receivers = [n for n in nodes if n.nodeid != transmitter.nodeid]
    rxs, rssis, snrs = calcReceivers(transmitter, receivers)
    rP.setTxRxs(transmitter, rxs)
    rP.setRSSISNR(rssis, snrs)
    for i,r in enumerate(rxs):
        forwardPacket(r.iface, packet, rssis[i], snrs[i])
    graph.packets.append(rP)


def calcReceivers(tx, receivers): 
    rxs = []
    rssis = []
    snrs = []
    for rx in receivers:
        dist_2d = calcDist(tx.x, tx.y, rx.x, rx.y) 
        pathLoss = estimatePathLoss(dist_2d, conf.FREQ)
        RSSI = conf.PTX + conf.GL - pathLoss
        SNR = RSSI-conf.NOISE_LEVEL
        if RSSI >= conf.SENSMODEM[conf.MODEM]:
            rxs.append(rx)
            rssis.append(RSSI)
            snrs.append(SNR)
    return rxs, rssis, snrs


def closeNodes():
    print("\nClosing all nodes...")
    pub.unsubAll()
    for n in nodes:
        n.iface.localNode.exitSimulator()


foundNodes = False
foundPath = False
for i in range(1, len(sys.argv)):
    if not "--p" in sys.argv[i] and not "/" in sys.argv[i]:
        if int(sys.argv[i]) > 10:
            print("Not sure if you want to start more than 10 terminals. Exiting.")
            exit(1)
        conf.NR_NODES = int(sys.argv[i])
        xs = []
        ys = []
        foundNodes = True
        break
if not foundNodes: 
    [xs, ys] = genScenario()
    conf.NR_NODES = len(xs)
if len(sys.argv) > 2 and "--p" in sys.argv[2]:
    string = sys.argv[3]
    pathToProgram = string
    foundPath = True
elif len(sys.argv) > 1:
    if "--p" in sys.argv[1]:
        string = sys.argv[2]
        pathToProgram = string
        foundPath = True
if not foundPath:
    pathToProgram = os.getcwd()+"/"

nodes = []
graph = Graph()
for n in range(conf.NR_NODES):
    if len(xs) == 0: 
        node = interactiveNode(nodes, n, n+HW_ID_OFFSET, n+TCP_PORT_OFFSET)
    else:
        node = interactiveNode(nodes, n, n+HW_ID_OFFSET, n+TCP_PORT_OFFSET, xs[n], ys[n])
    nodes.append(node)
    graph.addNode(node)

for n in nodes:
    cmdString = "gnome-terminal --title='Node "+str(n.nodeid)+"' -- "+pathToProgram+"program -e -d "+os.path.expanduser('~')+"/.portduino/node"+str(n.nodeid)+" -h "+str(n.hwId)+" -p "+str(n.TCPPort)
    os.system(cmdString) 

messages = []
global messageId
messageId = -1
time.sleep(4)  # Allow instances to start up their TCP service 
try:
    for n in nodes:
        iface = meshtastic.tcp_interface.TCPInterface(hostname="localhost", portNumber=n.TCPPort)
        n.addInterface(iface)
    pub.subscribe(onReceive, "meshtastic.receive.simulator")
except(Exception) as ex:
    print(f"Error: Could not connect to native program: {ex}")
    for n in nodes:
        n.iface.close()
    os.system("killall "+pathToProgram+"program")
    sys.exit(1)


try:
    time.sleep(15*conf.NR_NODES)  # Wait until nodeInfo messages are sent
    text = "Hi there, how are you doing?"

    # Broadcast Message from node 0
    fromNode = 0
    sendBroadcast(text, fromNode)

    # Direct Message from node 1 to node 0
    # fromNode = 1
    # toNode = 0
    # sendDM(text, fromNode, toNode)

    time.sleep(15)
    closeNodes()
except KeyboardInterrupt:
    closeNodes()

graph.initRoutes(nodes[0].iface.defaultHopLimit)