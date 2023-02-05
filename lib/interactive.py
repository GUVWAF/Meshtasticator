from meshtastic import tcp_interface, BROADCAST_NUM, mesh_pb2, \
	admin_pb2, telemetry_pb2, remote_hardware_pb2, portnums_pb2, channel_pb2
from pubsub import pub
from matplotlib import patches
from matplotlib.widgets import TextBox
from matplotlib import pyplot as plt
import sys
import os
import time
import cmd
from . import config as conf
from .common import *
HW_ID_OFFSET = 16
TCP_PORT_OFFSET = 4403


class interactiveNode(): 
  def __init__(self, nodes, nodeId, hwId, TCPPort, nodeConfig):
    self.nodeid = nodeId
    if nodeConfig is not None: 
      self.x = nodeConfig['x']
      self.y = nodeConfig['y']
      self.z = nodeConfig['z']
      self.isRouter = nodeConfig['isRouter']
      self.isRepeater = nodeConfig['isRepeater']
      self.hopLimit = nodeConfig['hopLimit']
      self.antennaGain = nodeConfig['antennaGain']
    else: 
      self.x, self.y = findRandomPosition(nodes)
      self.z = conf.HM
      self.isRouter = conf.router
      self.isRepeater = False
      self.hopLimit = conf.hopLimit
      self.antennaGain = conf.GL
    self.hwId = hwId
    self.TCPPort = TCPPort 


  def addInterface(self, iface):
    self.iface = iface

  
  def setConfig(self):
    if self.hopLimit != 3:
      loraConfig = self.iface.localNode.localConfig.lora
      setattr(self.iface.localNode.localConfig.lora, 'hop_limit', self.hopLimit)
      p = admin_pb2.AdminMessage()
      p.set_config.lora.CopyFrom(loraConfig)
      self.iface.localNode._sendAdmin(p)
    if self.isRouter:
      deviceConfig = self.iface.localNode.localConfig.device
      setattr(deviceConfig, 'role', "ROUTER")
      p = admin_pb2.AdminMessage()
      p.set_config.device.CopyFrom(deviceConfig)
      self.iface.localNode._sendAdmin(p)
    elif self.isRepeater:
      deviceConfig = self.iface.localNode.localConfig.device
      setattr(deviceConfig, 'role', 4)
      p = admin_pb2.AdminMessage()
      p.set_config.device.CopyFrom(deviceConfig)
      self.iface.localNode._sendAdmin(p)


  def addAdminChannel(self):
    ch = self.iface.localNode.getChannelByChannelIndex(1)
    chs = channel_pb2.ChannelSettings()
    chs.psk = b'\xb0X\xad\xb3\xa5\xd0?$\x8c\x92{\xcd^(\xeb\xb7\x01\x84"\xc9\xf4\x06:\x8d\xfdD#\x08\xe5\xc2\xd7\xdc'
    chs.name = "admin"
    ch.settings.CopyFrom(chs)
    ch.role = channel_pb2.Channel.Role.SECONDARY
    self.iface.localNode.channels[ch.index] = ch
    self.iface.localNode.writeChannel(ch.index)
    time.sleep(1)


class interactivePacket():
	def __init__(self, packet, id):
		self.packet = packet
		self.localId = id
        
	def setTxRxs(self, transmitter, receivers):
		self.transmitter = transmitter
		self.receivers = receivers

	def setRSSISNR(self, rssis, snrs):
		self.rssis = rssis
		self.snrs = snrs


class interactiveGraph(Graph):
  def __init__(self):
    super().__init__()
    self.routes = False


  def initRoutes(self, sim):
    if not sim.docker:
      sim.closeNodes()
    if not self.routes: 
      self.routes = True
      self.sim = sim
      self.arrows = []
      self.txts = []
      self.annots = []
      self.firstTime = True
      self.defaultHopLimit = conf.hopLimit
      self.fig.subplots_adjust(bottom=0.2)
      axbox = self.fig.add_axes([0.5, 0.04, 0.1, 0.06])
      self.text_box = TextBox(axbox, "Message ID: ", initial="0")
      self.text_box.disconnect("button_press_event")
      self.text_box.on_submit(self.submit)
      self.fig.canvas.mpl_connect("motion_notify_event", self.hover)
      self.fig.canvas.mpl_connect("button_press_event", self.onClick)
      self.fig.canvas.mpl_connect("close_event", self.onClose)
      print("Enter a message ID on the plot to show its route.")
      self.fig.canvas.draw_idle()
      self.fig.canvas.get_tk_widget().focus_set()
      plt.show()
    elif sim.docker:
      sim.closeNodes()


  def clearRoute(self):
    for arr in self.arrows.copy():
      arr.remove()
      self.arrows.remove(arr)
    for ann in self.annots.copy():
      ann.remove()
      self.annots.remove(ann)


  def plotRoute(self, messageId):
    if self.firstTime: 
      print('Hover over an arc to show some info and click to remove it afterwards.')
      print('Close the window to exit the simulator.')
    self.firstTime = False
    packets = [p for p in self.packets if p.localId == messageId]
    if len(packets) > 0:
      self.clearRoute()
      style = "Simple, tail_width=0.5, head_width=4, head_length=8"
      pairs = dict.fromkeys(list(set(p.transmitter for p in packets)), []) 
      for p in packets:
        tx = p.transmitter
        rxs = p.receivers
        rxCnt = 1
        for ri, rx in enumerate(rxs):
          # calculate how many packets with the same Tx and Rx we have
          found = False
          for pi, rxPair in enumerate(pairs.get(tx)): # pair is rx.nodeid and its count for this transmitter
            if rxPair[0] == rx.nodeid:
              found = True
              rxCnt = rxPair[1] + 1
              updated = pairs.get(tx).copy()
              updated[pi] = (rx.nodeid, rxCnt)
              pairs.update({tx: updated}) 
          if not found:
              rxCnt = 1
              pairs.get(tx).append((rx.nodeid, rxCnt))
          kw = dict(arrowstyle=style, color=plt.cm.Set1(tx.nodeid))
          rad = str(rxCnt*0.1) # set the rad to Tx-Rx pair count
          patch = patches.FancyArrowPatch((tx.x, tx.y), (rx.x, rx.y), connectionstyle="arc3,rad="+rad, **kw)
          self.ax.add_patch(patch)

          if int(p.packet["to"]) == BROADCAST_NUM:
            to = "All"
          else: 
            to = str(p.packet["to"]-HW_ID_OFFSET)

          if "hopLimit" in p.packet:
            hopLimit = p.packet["hopLimit"]
          else:
            hopLimit = None

          if p.packet["from"] == tx.hwId:
            if "requestId" in p.packet["decoded"]:
              if p.packet["priority"] == "ACK":
                msgType = "Real\/ACK"
              else:
                msgType = "Response"
            else:
              msgType = "Original\/message"
          elif "requestId" in p.packet["decoded"]:
            if p.packet["decoded"]["simulator"]["portnum"] == "ROUTING_APP":
              msgType = "Forwarding\/real\/ACK"
            else: 
              msgType = "Forwarding\/response"
          else:
            if int(p.packet['from'])-HW_ID_OFFSET == rx.nodeid:
              msgType = "Implicit\/ACK"
            else: 
              if to == "All":
                msgType = "Rebroadcast"
              else:
                msgType = "Forwarding\/message"

          fields = []
          msgTypeField = r"$\bf{"+msgType+"}$"
          fields.append(msgTypeField)
          origSenderField = "Original sender: "+str(p.packet["from"]-HW_ID_OFFSET)
          fields.append(origSenderField)
          destField = "Destination: "+to
          fields.append(destField)
          portNumField = "Portnum: "+str(p.packet["decoded"]["simulator"]["portnum"])
          fields.append(portNumField)
          if hopLimit:
            hopLimitField = "HopLimit: "+str(hopLimit)
            fields.append(hopLimitField)
          rssiField = "RSSI: "+str(round(p.rssis[ri], 2)) +" dBm"
          fields.append(rssiField)
          table = ""
          for i,f in enumerate(fields): 
            table += f
            if i != len(fields)-1:
              table += "\n"
          annot = self.ax.annotate(table, xy=((tx.x+rx.x)/2, rx.y+150), bbox=dict(boxstyle="round", fc="w"))
          annot.get_bbox_patch().set_facecolor(patch.get_facecolor())
          annot.get_bbox_patch().set_alpha(0.4)
          annot.set_visible(False)
          self.arrows.append(patch)
          self.annots.append(annot)
      self.fig.canvas.draw_idle() 
      self.fig.suptitle('Route of message '+str(messageId)+' and ACKs')
    else:
      print('Could not find message ID.')


  def hover(self, event):
    if event.inaxes == self.ax:
      for i,a in enumerate(self.arrows):
        annot = self.annots[i]
        cont, _ = a.contains(event)
        if cont:
          annot.set_visible(True)
          self.fig.canvas.draw()
          break

  def onClick(self, event):
    for annot in self.annots:
      if annot.get_visible():
        annot.set_visible(False)
        self.fig.canvas.draw_idle()

  def onClose(self, event):
    self.sim.closeNodes()

  def submit(self, val):
    messageId = int(val)
    self.plotRoute(messageId)


class interactiveSim(): 
  def __init__(self):
    self.script = False
    self.messages = []
    self.messageId = -1
    self.nodes = []
    foundNodes = False
    foundPath = False
    self.docker = False
    for i in range(1, len(sys.argv)):
      if "--s" in sys.argv[i] or "--script" in sys.argv[i]:
        self.script = True
      elif "--d" in sys.argv[i] or "--docker" in sys.argv[i]:
        self.docker = True
      elif not "--p" in sys.argv[i] and not "/" in sys.argv[i]:
        if int(sys.argv[i]) > 10:
          print("Not sure if you want to start more than 10 terminals. Exiting.")
          exit(1)
        conf.NR_NODES = int(sys.argv[i])
        foundNodes = True
        config = [None for _ in range(conf.NR_NODES)]
    if not foundNodes: 
      config = genScenario()
      conf.NR_NODES = len(config.keys())
    if len(sys.argv) > 2 and "--p" in sys.argv[2]:
      string = sys.argv[3]
      pathToProgram = string
      foundPath = True
    elif len(sys.argv) > 1:
      if "--p" in sys.argv[1]:
        string = sys.argv[2]
        pathToProgram = string
        foundPath = True
    if not foundPath and not self.docker:
      pathToProgram = os.getcwd()+"/"
    if not self.docker and not sys.platform.startswith('linux'):
      print("Docker is required for non-Linux OS.")
      self.docker = True

    self.graph = interactiveGraph()
    for n in range(conf.NR_NODES):
      node = interactiveNode(self.nodes, n, n+HW_ID_OFFSET, n+TCP_PORT_OFFSET, config[n])
      self.nodes.append(node)
      self.graph.addNode(node)

    if self.docker:
      import docker
      n0 = self.nodes[0]
      dockerClient = docker.from_env()
      if sys.platform == "darwin":
        self.container = dockerClient.containers.run("meshtastic-device", \
          "./meshtasticd_linux_amd64 -e -d /home/node"+str(n0.nodeid)+" -h "+str(n0.hwId)+" -p "+str(n0.TCPPort), \
          ports=dict(zip((str(n.TCPPort)+'/tcp' for n in self.nodes), (n.TCPPort for n in self.nodes))), detach=True, auto_remove=True, user="root")
        for n in self.nodes[1:]:
          self.container.exec_run("./meshtasticd_linux_amd64 -e -d /home/node"+str(n.nodeid)+" -h "+str(n.hwId)+" -p "+str(n.TCPPort), detach=True, user="root") 
        print("Docker container with name "+str(self.container.name)+" is started.")
      else: 
        self.container = dockerClient.containers.run("meshtastic-device", \
          "sh -c './meshtasticd_linux_amd64 -e -d /home/node"+str(n0.nodeid)+" -h "+str(n0.hwId)+" -p "+str(n0.TCPPort)+" > /home/out_"+str(n0.nodeid)+".log'", \
          ports=dict(zip((str(n.TCPPort)+'/tcp' for n in self.nodes), (n.TCPPort for n in self.nodes))), detach=True, auto_remove=True, user="root")
        for n in self.nodes[1:]:
          self.container.exec_run("sh -c './meshtasticd_linux_amd64 -e -d /home/node"+str(n.nodeid)+" -h "+str(n.hwId)+" -p "+str(n.TCPPort)+" > /home/out_"+str(n.nodeid)+".log'", detach=True, user="root") 
        print("Docker container with name "+str(self.container.name)+" is started.")
        print("You can check the device logs using 'docker exec -it "+str(self.container.name) +" cat /home/out_x.log', where x is the node number.")
    else: 
      from shutil import which
      if which('gnome-terminal') is not None:
        xterm = False
      elif which('xterm') is not None: 
        xterm = True
      else:
        print('The interactive simulator on native Linux (without Docker) requires either gnome-terminal or xterm.')
        exit(1)
      for n in self.nodes:
        if not xterm:
          newTerminal = "gnome-terminal --title='Node "+str(n.nodeid)+"' -- "
        else: 
          newTerminal = "xterm -title 'Node "+str(n.nodeid)+"' -e "
        startNode = "program -e -d "+os.path.expanduser('~')+"/.portduino/node"+str(n.nodeid)+" -h "+str(n.hwId)+" -p "+str(n.TCPPort)+ " &"
        cmdString = newTerminal+pathToProgram+startNode
        os.system(cmdString)  

    time.sleep(4)  # Allow instances to start up their TCP service 
    try:
      for n in self.nodes:
        iface = tcp_interface.TCPInterface(hostname="localhost", portNumber=n.TCPPort)
        n.addInterface(iface)
      pub.subscribe(self.onReceive, "meshtastic.receive.simulator")
      for n in self.nodes:
        n.setConfig()
    except(Exception) as ex:
      print(f"Error: Could not connect to native program: {ex}")
      self.closeNodes()
      sys.exit(1)


  def forwardPacket(self, iface, packet, rssi, snr): 
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
    if "channel" in packet:
      meshPacket.channel = int(packet["channel"])
    meshPacket.rx_rssi = int(rssi) 
    meshPacket.rx_snr = int(snr)  
    toRadio = mesh_pb2.ToRadio()
    toRadio.packet.CopyFrom(meshPacket)
    iface._sendToRadio(toRadio)


  def showNodes(self, id=None):
    if id != None: 
      print('NodeDB as seen by node', id)
      self.nodes[id].iface.showNodes()
    else: 
      for n in self.nodes:
        print('NodeDB as seen by node', n.nodeid)
        n.iface.showNodes()


  def sendBroadcast(self, text, fromNode):
    self.nodes[fromNode].iface.sendText(text)


  def sendDM(self, text, fromNode, toNode):
    self.nodes[fromNode].iface.sendText(text, destinationId=self.nodes[toNode].hwId, wantAck=True)


  def sendPing(self, fromNode, toNode):
    payload = str.encode("test string")
    self.nodes[fromNode].iface.sendData(payload, self.nodes[toNode].hwId, portNum=portnums_pb2.PortNum.REPLY_APP,
      wantAck=True, wantResponse=True)


  def traceRoute(self, fromNode, toNode):
    r = mesh_pb2.RouteDiscovery()
    self.nodes[fromNode].iface.sendData(r, destinationId=self.nodes[toNode].hwId, portNum=70, wantResponse=True)


  def requestPosition(self, fromNode, toNode):
    self.nodes[fromNode].iface.sendPosition(destinationId=self.nodes[toNode].hwId, wantResponse=True)


  def getNodeById(self, id):
    return self.nodes[id].iface.localNode

  
  def nodeIdToDest(self, id):
    val = hex(id+HW_ID_OFFSET).strip('0x')
    return '!'+'0'*(8-len(val))+val


  def sendFromTo(self, fromNode, toNode):
    return self.nodes[fromNode].iface.getNode(self.nodeIdToDest(toNode))  


  def onReceive(self, interface, packet): 
    if "requestId" in packet["decoded"]:
      # Packet with requestId is coupled to original message
      existingMsgId = next((m.localId for m in self.messages if m.packet["id"] == packet["decoded"]["requestId"]), None)
      if existingMsgId == None:
          print('Could not find requestId!\n')
      mId = existingMsgId
    else:
      existingMsgId = next((m.localId for m in self.messages if m.packet["id"] == packet["id"]), None)
      if existingMsgId != None:
          mId = existingMsgId
      else: 
          self.messageId += 1
          mId = self.messageId
    rP = interactivePacket(packet, mId)
    self.messages.append(rP)
    if self.script:
      print("Node", interface.myInfo.my_node_num-HW_ID_OFFSET, "sent", packet["decoded"]["simulator"]["portnum"], "with id", mId, "over the air!")
    transmitter = next((n for n in self.nodes if n.TCPPort == interface.portNumber), None)
    receivers = [n for n in self.nodes if n.nodeid != transmitter.nodeid]
    rxs, rssis, snrs = self.calcReceivers(transmitter, receivers)
    rP.setTxRxs(transmitter, rxs)
    rP.setRSSISNR(rssis, snrs)
    for i,r in enumerate(rxs):
      self.forwardPacket(r.iface, packet, rssis[i], snrs[i])
    self.graph.packets.append(rP)


  def calcReceivers(self, tx, receivers): 
    rxs = []
    rssis = []
    snrs = []
    for rx in receivers:
      dist_3d = calcDist(tx.x, rx.x, tx.y, rx.y, tx.z, rx.z) 
      pathLoss = phy.estimatePathLoss(dist_3d, conf.FREQ, tx.z, rx.z)
      RSSI = conf.PTX + tx.antennaGain + rx.antennaGain - pathLoss
      SNR = RSSI-conf.NOISE_LEVEL
      if RSSI >= conf.SENSMODEM[conf.MODEM]:
        rxs.append(rx)
        rssis.append(RSSI)
        snrs.append(SNR)
    return rxs, rssis, snrs


  def closeNodes(self):
    print("\nClosing all nodes...")
    pub.unsubAll()
    for n in self.nodes:
      n.iface.localNode.exitSimulator()
    if self.docker:
      self.container.stop()


class CommandProcessor(cmd.Cmd):
    def cmdloop(self, sim):
        self.sim = sim
        print("Type 'help' to list the available commands for sending messages. Type 'plot' to show the routes or 'exit' to exit the simulator.")
        return cmd.Cmd.cmdloop(self)


    def do_broadcast(self, line):
        """broadcast <fromNode> <txt>
        Send a broadcast from node \x1B[3mfromNode\x1B[0m with text \x1B[3mtxt\x1B[0m."""
        arguments = line.split()
        if len(arguments) < 2:
            print('Please use the syntax: "broadcast <fromNode> <txt>"')
            return False
        fromNode = int(arguments[0])
        if fromNode >= len(self.sim.nodes):
            print('Node ID', fromNode, 'is outside the range of nodes.')
            return False
        txt = ""
        for s in arguments[1:-1]:
            txt += s+" "
        txt += arguments[-1]
        print('Instructing node', fromNode, 'to broadcast '+'"'+txt+'"', '(message ID =', str(self.sim.messageId+1)+')')
        self.sim.sendBroadcast(txt, fromNode)


    def do_DM(self, line):
        """DM <fromNode> <toNode> <txt>
        Send a Direct Message from node \x1B[3mfromNode\x1B[0m to node \x1B[3mtoNode\x1B[0m with text \x1B[3mtxt\x1B[0m."""
        arguments = line.split()
        if len(arguments) < 3:
            print('Please use the syntax: "DM <fromNode> <toNode> <txt>"')
            return False
        fromNode = int(arguments[0])
        if fromNode >= len(self.sim.nodes):
            print('Node ID', fromNode, 'is outside the range of nodes.')
            return False
        toNode = int(arguments[1])
        if toNode >= len(self.sim.nodes):
            print('Node ID', toNode, 'is outside the range of nodes.')
            return False
        txt = ""
        for s in arguments[2:-1]:
            txt += s+" "
        txt += arguments[-1]
        print('Instructing node', fromNode, 'to DM node', str(toNode)+' "'+txt+'"', '(message ID =', str(self.sim.messageId+1)+')')
        self.sim.sendDM(txt, fromNode, toNode)


    def do_ping(self, line):
        """ping <fromNode> <toNode>
        Send ping from node \x1B[3mfromNode\x1B[0m to node \x1B[3mtoNode\x1B[0m."""
        arguments = line.split()
        if len(arguments) != 2:
            print('Please use the syntax: "ping <fromNode> <toNode>"')
            return False
        fromNode = int(arguments[0])
        if fromNode >= len(self.sim.nodes):
            print('Node ID', fromNode, 'is outside the range of nodes.')
            return False
        toNode = int(arguments[1])
        if toNode >= len(self.sim.nodes):
            print('Node ID', toNode, 'is outside the range of nodes.')
            return False
        print('Instructing node', fromNode, 'to send ping to node', toNode, '(message ID =', str(self.sim.messageId+1)+')')
        self.sim.sendPing(fromNode, toNode)


    def do_traceroute(self, line):
        """traceroute <fromNode> <toNode>
        Send a traceroute request from node \x1B[3mfromNode\x1B[0m to node \x1B[3mtoNode\x1B[0m."""
        arguments = line.split()
        if len(arguments) != 2:
            print('Please use the syntax: "traceroute <fromNode> <toNode>"')
            return False
        fromNode = int(arguments[0])
        if fromNode >= len(self.sim.nodes):
            print('Node ID', fromNode, 'is outside the range of nodes.')
            return False
        toNode = int(arguments[1])
        if toNode >= len(self.sim.nodes):
            print('Node ID', toNode, 'is outside the range of nodes.')
            return False
        print('Instructing node', fromNode, 'to send traceroute request to node', toNode, '(message ID =', str(self.sim.messageId+1)+')')
        print('This takes a while, the result will be in the log of node '+str(fromNode)+'.')
        self.sim.traceRoute(fromNode, toNode)


    def do_reqPos(self, line):
        """reqPos <fromNode> <toNode>
        Send a position request from node \x1B[3mfromNode\x1B[0m to node \x1B[3mtoNode\x1B[0m."""
        arguments = line.split()
        if len(arguments) != 2:
            print('Please use the syntax: "reqPos <fromNode> <toNode>"')
            return False
        fromNode = int(arguments[0])
        if fromNode >= len(self.sim.nodes):
            print('Node ID', fromNode, 'is outside the range of nodes.')
            return False
        toNode = int(arguments[1])
        if toNode >= len(self.sim.nodes):
            print('Node ID', toNode, 'is outside the range of nodes.')
            return False
        print('Instructing node', fromNode, 'to send position request to node', toNode, '(message ID =', str(self.sim.messageId+1)+')')
        self.sim.requestPosition(fromNode, toNode)


    def do_nodes(self, line):
        """nodes <id0> [id1, etc.]
        Show the node list as seen by node(s) \x1B[3mid0\x1B[0m, \x1B[3mid1\x1B[0m., etc."""
        arguments = line.split()
        if len(arguments) < 1:
            print('Please use the syntax: "nodes <id0> [id1, etc.]"')
            return False
        for n in arguments:
            if int(n) >= len(self.sim.nodes):
                print('Node ID', n, 'is outside the range of nodes.')
                continue
            self.sim.showNodes(int(n))


    def do_plot(self, line):
        """plot
        Plot the routes of messages sent."""
        self.sim.graph.initRoutes(self.sim)
        return True


    def do_exit(self, line):
        """exit
        Exit the simulator without plotting routes."""
        self.sim.closeNodes()
        return True  
    
