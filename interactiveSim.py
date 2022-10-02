""" Simulator for letting multiple instances of native programs 
    communicate via TCP as if they did via their LoRa chip. 
    Usage: python3 interactiveSim.py [nrNodes] [--p <full-path-to-program>]
"""

import sys
import os
import time
from pubsub import pub
import meshtastic.tcp_interface
from meshtastic import mesh_pb2
HW_ID_OFFSET = 16
TCP_PORT_OFFSET = 4403


def forwardPacket(iface, packet): 
    data = packet["decoded"]["payload"]
    if getattr(data, "SerializeToString", None):
        data = data.SerializeToString()

    if len(data) > mesh_pb2.Constants.DATA_PAYLOAD_LEN:
        raise Exception("Data payload too big")

    meshPacket = mesh_pb2.MeshPacket()
    meshPacket.decoded.payload = data
    meshPacket.to = packet["to"]
    setattr(meshPacket, "from", packet["from"])
    meshPacket.id = packet["id"]
    if "want_ack" in packet:
        meshPacket.want_ack = packet["want_ack"]
    else:
        meshPacket.want_ack = False
    meshPacket.decoded.portnum = 69
    if "hopLimit" in packet:
        meshPacket.hop_limit = packet["hopLimit"]
    if "want_response" in packet:
        meshPacket.decoded.want_response = packet["want_response"]
    else:
        meshPacket.decoded.want_response = False
    meshPacket.rx_rssi = 10  # TODO calculate based on positions
    meshPacket.rx_snr = -10  # TODO calculate based on positions
    toRadio = mesh_pb2.ToRadio()
    toRadio.packet.CopyFrom(meshPacket)
    iface._sendToRadio(toRadio)


def onReceive(interface, packet, ifaceList): 
    print("Node", interface.myInfo.my_node_num-HW_ID_OFFSET, "sent", packet["decoded"]["simulator"]["portnum"], "with id", packet["id"], "over the air!")
    # TODO forward only to those nodes that are in range 
    for i in [iface for iface in ifaceList if iface.portNumber != interface.portNumber]:
        forwardPacket(i, packet)


if len(sys.argv) < 2:
    print("Number of nodes not specified, picked 2.")
    nrNodes = 2
    pathToProgram = os.getcwd()+"/"
else:
    if int(sys.argv[1]) > 10:
        print("Not sure if you want to start more than 10 terminals. Exiting.")
        exit(1)
    nrNodes = int(sys.argv[1])
    if len(sys.argv) > 2 and type(sys.argv[2]) == str and ("--p" in sys.argv[2]):
        string = sys.argv[3]
        pathToProgram = string
    else:
        pathToProgram = os.getcwd()+"/"
        

nodeIds = range(nrNodes)
hwIds = range(HW_ID_OFFSET, HW_ID_OFFSET+nrNodes)
portNums = range(TCP_PORT_OFFSET, TCP_PORT_OFFSET+nrNodes)
for n,h,p in zip(nodeIds, hwIds, portNums):
    cmdString = "gnome-terminal --title='Node "+str(n)+"' -- "+pathToProgram+"program -e -d "+os.path.expanduser('~')+"/.portduino/node"+str(n)+" -h "+str(h)+" -p "+str(p)
    os.system(cmdString) 

time.sleep(4)  # Allow instances to start up their TCP service 

ifaceList = []
try:
    for p in portNums:
        iface = meshtastic.tcp_interface.TCPInterface(hostname="localhost", portNumber=p)
        ifaceList.append(iface)
    pub.subscribe(onReceive, "meshtastic.receive.simulator", ifaceList=ifaceList)
except(Exception) as ex:
    print(f"Error: Could not connect to native program: {ex}")
    for i in ifaceList:
        i.close()
    os.system("killall "+pathToProgram+"program")
    sys.exit(1)

try:
    while True:
        time.sleep(40)  # Wait until nodeInfo messages are sent
        text = "Hi there, how are you doing?"
        ifaceList[0].sendText(text)
        # Add any additional messaging here
        time.sleep(300)

except KeyboardInterrupt:
    print("\nClosing all nodes...")
    for i in ifaceList:
        i.close()
    os.system("killall "+pathToProgram+"program")
    sys.exit(1)


