#!/usr/bin/env python3
import simpy
import sys
import lib.config as conf
from lib.common import *
from lib.mac import *
from lib.packet import * 

VERBOSE = True
random.seed(conf.SEED)


class MeshNode():
	def __init__(self, nodes, env, bc_pipe, nodeid, period, messages, packetsAtN, packets, delays, x=-1, y=-1):
		self.nodeid = nodeid
		self.x = x
		self.y = y
		self.messageSeq = messageSeq
		self.env = env
		self.period = period
		self.bc_pipe = bc_pipe
		self.rx_snr = 0
		self.isRouter = False
		self.nodes = nodes
		self.messages = messages
		self.packetsAtN = packetsAtN
		self.nrPacketsSent = 0
		self.packets = packets
		self.delays = delays
		self.leastReceivedHopLimit = {}
		self.isReceiving = []
		self.isTransmitting = False
		self.usefulPackets = 0
		self.txAirUtilization = 0

		if x == -1 and y == -1: 
			foundMin = True
			foundMax = False
			tries = 0
			while not (foundMin and foundMax):
				a = random.random()
				b = random.random()
				if b < a:
					a,b = b,a
				posx = b*conf.RAY*math.cos(2*math.pi*a/b)+conf.OX
				posy = b*conf.RAY*math.sin(2*math.pi*a/b)+conf.OY
				if len(nodes) > 0:
					for n in nodes:
						dist = np.sqrt(((abs(n.x-posx))**2)+((abs(n.y-posy))**2))
						if dist < conf.MINDIST:
							foundMin = False
							break
						pathLoss = estimatePathLoss(dist, conf.REGION["freq_start"])
						rssi = conf.PTX + conf.GL - pathLoss
						if rssi >= conf.SENSMODEM[conf.MODEM]:
							foundMax = True
					if foundMin and foundMax:
						self.x = posx
						self.y = posy
				else:
					self.x = posx
					self.y = posy
					foundMin = True
					foundMax = True
				tries += 1
				if tries > 1000:
					print('Could not find a location to place the node. Try increasing RAY or decreasing MINDIST.')
					break

		env.process(self.generateMessage())
		env.process(self.receive(self.bc_pipe.get_output_conn()))
		self.transmitter = simpy.Resource(env, 1)


	def generateMessage(self):
		global messageSeq
		while True:	
			nextGen = random.expovariate(1.0/float(self.period))
			# do not generate message near the end of the simulation (otherwise flooding cannot finish in time)
			if self.env.now+nextGen+conf.hopLimit*airtime(conf.SFMODEM[conf.MODEM], conf.CRMODEM[conf.MODEM], conf.PACKETLENGTH, conf.BWMODEM[conf.MODEM]) < conf.SIMTIME:
				yield self.env.timeout(nextGen) 

				messageSeq += 1
				self.messages.append(MeshMessage(self.nodeid, self.env.now, messageSeq))
				p = MeshPacket(self.nodes, self.nodeid, self.nodeid, self.x, self.y, conf.PACKETLENGTH, messageSeq, self.env.now)  
				verboseprint('At time', round(self.env.now, 3), 'node', self.nodeid, 'generated message', p.seq)
				self.packets.append(p)
				self.env.process(self.transmit(p))
				while True: # ReliableRouter: retransmit message if no ACK received after timeout 
					retransmissionMsec = getRetransmissionMsec(p) 
					yield self.env.timeout(retransmissionMsec)

					ackReceived = False  # check whether you received an ACK on the transmitted message
					minRetransmissions = conf.maxRetransmission
					for packetSent in self.packets:
						if packetSent.origTxNodeId == self.nodeid and packetSent.seq == p.seq:
							if packetSent.retransmissions < minRetransmissions:
								minRetransmissions = packetSent.retransmissions
							if packetSent.ackReceived:
								ackReceived = True
					if ackReceived: 
						verboseprint('Node', self.nodeid, 'received ACK on generated message with seq. nr.', p.seq)
						break
					else: 
						if minRetransmissions > 0:  # generate new packet with same sequence number
							pNew = MeshPacket(self.nodes, self.nodeid, self.nodeid, self.x, self.y, conf.PACKETLENGTH, p.seq, p.genTime)  
							pNew.retransmissions = minRetransmissions-1
							verboseprint('At time', round(self.env.now, 3), 'node', self.nodeid, 'wants to retransmit its generated packet', p.seq, 'minRetransmissions', minRetransmissions)
							self.packets.append(pNew)							
							self.env.process(self.transmit(pNew))
						else:
							verboseprint('At time', round(self.env.now, 3), 'node', self.nodeid, 'reliable send of', p.seq, 'failed.')
							break
			else:  # do not send this message anymore, since it is close to the end of the simulation
				break


	def transmit(self, packet):
		with self.transmitter.request() as request:
			yield request

			# listen-before-talk from src/mesh/RadioLibInterface.cpp 
			txTime = setTransmitDelay(self, packet) 
			verboseprint('At time', round(self.env.now, 3), 'node', self.nodeid, 'picked wait time', txTime)
			yield self.env.timeout(txTime)

			# wait when currently receiving or transmitting, or channel is active
			while any(self.isReceiving) or self.isTransmitting or isChannelActive(self, self.env):
				verboseprint('At time', round(self.env.now, 3), 'node', self.nodeid, 'is busy Tx-ing', self.isTransmitting, 'or Rx-ing', any(self.isReceiving), 'else channel busy!')
				txTime = setTransmitDelay(self, packet) 
				yield self.env.timeout(txTime)
			verboseprint('At time', round(self.env.now, 3), 'node', self.nodeid, 'ends waiting')	

			# check if you received an ACK for this message in the meantime
			if packet.seq not in self.leastReceivedHopLimit:
				self.leastReceivedHopLimit[packet.seq] = packet.hopLimit+1 
			if self.leastReceivedHopLimit[packet.seq] > packet.hopLimit:  # no ACK received yet, so may start transmitting 
				verboseprint('At time', round(self.env.now, 3), 'node', self.nodeid, 'started low level send', packet.seq, 'hopLimit', packet.hopLimit, 'original Tx', packet.origTxNodeId)
				self.nrPacketsSent += 1
				for rx_node in self.nodes:
					if packet.sensedByN[rx_node.nodeid] == True:
						if (checkcollision(self.env, packet, rx_node.nodeid, self.packetsAtN) == 0):
							self.packetsAtN[rx_node.nodeid].append(packet)
				packet.startTime = self.env.now
				packet.endTime = self.env.now + packet.timeOnAir
				self.txAirUtilization += packet.timeOnAir
				self.bc_pipe.put(packet)
				self.isTransmitting = True
				yield self.env.timeout(packet.timeOnAir)
				self.isTransmitting = False
			else:  # received ACK: abort transmit, remove from packets generated 
				verboseprint('At time', round(self.env.now, 3), 'node', self.nodeid, 'in the meantime received ACK, abort packet with seq. nr', packet.seq)
				self.packets.remove(packet)


	def receive(self, in_pipe):
		while True:
			p = yield in_pipe.get()
			if p.sensedByN[self.nodeid] and not p.collidedAtN[self.nodeid] and p.onAirToN[self.nodeid]:  # start of reception
				if not self.isTransmitting:
					verboseprint('At time', round(self.env.now, 3), 'node', self.nodeid, 'started receiving packet', p.seq, 'from', p.txNodeId)
					p.onAirToN[self.nodeid] = False 
					self.isReceiving.append(True)
				else:  # if you were currently transmitting, you could not have sensed it
					verboseprint('At time', round(self.env.now, 3), 'node', self.nodeid, 'was transmitting, so could not receive packet', p.seq)
					p.sensedByN[self.nodeid] = False
					p.onAirToN[self.nodeid] = False
			elif p.sensedByN[self.nodeid]:  # end of reception
				try: 
					self.isReceiving[self.isReceiving.index(True)] = False 
				except: 
					pass
				if p.collidedAtN[self.nodeid]:
					verboseprint('At time', round(self.env.now, 3), 'node', self.nodeid, 'could not decode packet.')
					continue
				p.receivedAtN[self.nodeid] = True
				verboseprint('At time', round(self.env.now, 3), 'node', self.nodeid, 'received packet', p.seq, 'with delay', round(env.now-p.genTime, 2))
				delays.append(env.now-p.genTime)
				
				# update hopLimit for this message
				if p.seq not in self.leastReceivedHopLimit:  # did not yet receive packet with this seq nr.
					# verboseprint('Node', self.nodeid, 'received packet nr.', p.seq, 'orig. Tx', p.origTxNodeId, "for the first time.")
					self.usefulPackets += 1
					self.leastReceivedHopLimit[p.seq] = p.hopLimit
				if p.hopLimit < self.leastReceivedHopLimit[p.seq]:  # hop limit of received packet is lower than previously received one
					self.leastReceivedHopLimit[p.seq] = p.hopLimit	

				# check if ACK for own generated message
				if p.origTxNodeId == self.nodeid: 
					# verboseprint("Node", self.nodeid, 'received ACK on generated message.')
					p.ackReceived = True
					continue
				
				# check if ACK for message you currently have in queue
				ackReceived = False		
				for sentPacket in self.packets:
					if sentPacket.txNodeId == self.nodeid and sentPacket.seq == p.seq:
						ackReceived = True
						sentPacket.ackReceived = True
				
				# FloodingRouter: rebroadcasting received message 
				if not ackReceived and p.hopLimit > 0:
					pNew = MeshPacket(self.nodes, p.origTxNodeId, self.nodeid, self.x, self.y, conf.PACKETLENGTH, p.seq, p.genTime) 
					pNew.hopLimit = p.hopLimit-1
					self.packets.append(pNew)
					self.env.process(self.transmit(pNew))


if VERBOSE:
	def verboseprint(*args, **kwargs): 
		print(*args, **kwargs)
else:   
	def verboseprint(*args, **kwargs): 
		pass


# simulation variables
nodes = []
messages = []
packets = []
delays = []
packetsAtN = [[] for _ in range(conf.NR_NODES)]
messageSeq = 0

getParams(sys.argv)	
env = simpy.Environment()
bc_pipe = BroadcastPipe(env)

graph = Graph()
for i in range(conf.NR_NODES):
	if len(conf.xs) == 0: 
		node = MeshNode(nodes, env, bc_pipe, i, conf.PERIOD, messages, packetsAtN, packets, delays)
	else: 
		node = MeshNode(nodes, env, bc_pipe, i, conf.PERIOD, messages, packetsAtN, packets, delays, conf.xs[i], conf.ys[i])
	nodes.append(node)
	graph.add(node)

# start simulation
print("\n====== START OF SIMULATION ======")
env.run(until=conf.SIMTIME)

# compute statistics
print("\n====== END OF SIMULATION ======")
print('Number of messages created:', messageSeq)
sent = len(packets)
potentialReceivers = sent*(conf.NR_NODES-1)
print('Number of packets sent:', sent, 'to', potentialReceivers, 'potential receivers')
nrCollisions = sum([1 for p in packets for n in nodes if p.collidedAtN[n.nodeid] == True])
print("Number of collisions:", nrCollisions)
nrSensed = sum([1 for p in packets for n in nodes if p.sensedByN[n.nodeid] == True])
print("Number of packets sensed:", nrSensed)
nrReceived = sum([1 for p in packets for n in nodes if p.receivedAtN[n.nodeid] == True])
print("Number of packets received:", nrReceived)
meanDelay = np.nanmean(delays)
print('Delay average (ms):', round(meanDelay, 2))
txAirUtilization = sum([n.txAirUtilization for n in nodes])/conf.NR_NODES/conf.SIMTIME*100
print('Average Tx air utilization:', round(txAirUtilization, 2), '%')
if nrSensed != 0:
	collisionRate = float((nrCollisions)/nrSensed)
	print("Percentage of packets that collided:", round(collisionRate*100, 2))
else:
	print("No packets sensed.")
nodeReach = sum([n.usefulPackets for n in nodes])/(messageSeq*(conf.NR_NODES-1))
print("Average percentage of nodes reached:", round(nodeReach*100, 2))
if nrReceived != 0:
	usefulness = sum([n.usefulPackets for n in nodes])/nrReceived  # nr of packets that delivered to a packet to a new receiver out of all packets sent
	print("Percentage of received packets containing new message:", round(usefulness*100, 2))
else:
	print('No packets received.')
graph.save()

if conf.PLOT:
	plotSchedule(packets, messages)
