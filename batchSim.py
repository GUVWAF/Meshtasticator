#!/usr/bin/env python3
import simpy
import numpy as np
import matplotlib
from matplotlib import pyplot as plt
matplotlib.use("TkAgg")
import lib.config as conf
from lib.common import *
from lib.packet import *
from lib.mac import *

VERBOSE = False
SAVE = True

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
		self.airUtilization = 0

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
					retransmissionMsec = getRetransmissionMsec(self, p) 
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
				self.airUtilization += packet.timeOnAir
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
				self.airUtilization += p.timeOnAir
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


repetitions = 100
parameters = [3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 20, 25]
collisions = []
reachability = []
usefulness = []
meanDelays = []
meanTxAirUtils = []
collisionStds = []
reachabilityStds = []
usefulnessStds = []
delayStds = []
txAirUtilsStds = []
for p, nrNodes in enumerate(parameters):
	conf.NR_NODES = nrNodes
	nodeReach = [0 for _ in range(repetitions)]
	nodeUsefulness = [0 for _ in range(repetitions)]
	collisionRate = [0 for _ in range(repetitions)]
	meanDelay = [0 for _ in range(repetitions)]
	meanTxAirUtilization = [0 for _ in range(repetitions)]
	print("\nStart of", p+1, "out of", len(parameters), "value", nrNodes)
	for rep in range(repetitions):
		setBatch(rep)
		random.seed(rep)
		env = simpy.Environment()
		bc_pipe = BroadcastPipe(env)

		nodes = []
		messages = []
		packets = []
		delays = []
		packetsAtN = [[] for _ in range(conf.NR_NODES)]
		messageSeq = 0

		found = False
		while not found:
			nodes = []
			for nodeId in range(conf.NR_NODES):
				if len(conf.xs) == 0: 
					node = MeshNode(nodes, env, bc_pipe, nodeId, conf.PERIOD, messages, packetsAtN, packets, delays)
					if node.x == -1:
						break
				nodes.append(node)
			if len(nodes) == conf.NR_NODES:
				found = True

		# start simulation
		env.run(until=conf.SIMTIME)
		nrCollisions = sum([1 for p in packets for n in nodes if p.collidedAtN[n.nodeid] == True])
		nrSensed = sum([1 for p in packets for n in nodes if p.sensedByN[n.nodeid] == True])
		nrReceived = sum([1 for p in packets for n in nodes if p.receivedAtN[n.nodeid] == True])
		nrUseful = sum([n.usefulPackets for n in nodes])
		if nrSensed != 0:
			collisionRate[rep] = float((nrCollisions)/nrSensed)*100
		else:
			collisionRate[rep] = np.NaN
		if messageSeq != 0: 
			nodeReach[rep] = nrUseful/(messageSeq*(conf.NR_NODES-1))*100
		else: 
			nodeReach[rep] = np.NaN
		if nrReceived != 0:
			nodeUsefulness[rep] = nrUseful/nrReceived*100  # nr of packets that delivered to a message to a new receiver out of all packets received
		else: 
			nodeUsefulness[rep] = np.NaN
		meanDelay[rep] = np.nanmean(delays)
		meanTxAirUtilization[rep] = sum([n.txAirUtilization for n in nodes])/conf.NR_NODES
	if SAVE:
		print('Saving to file...')
		data = {
			"CollisionRate": collisionRate,
			"Reachability": nodeReach, 
			"Usefulness": nodeUsefulness,
			"meanDelay": meanDelay,
			"meanTxAirUtil": meanTxAirUtilization,
			"nrCollisions": nrCollisions,
			"nrSensed": nrSensed,
			"nrReceived": nrReceived,
			"usefulPackets": nrUseful, 
			"MODEM": conf.NR_NODES, 
			"MODEL": conf.MODEL,
			"NR_NODES": conf.NR_NODES,
			"INTERFERENCE_LEVEL": conf.INTERFERENCE_LEVEL,
			"COLLISION_DUE_TO_INTERFERENCE": conf.COLLISION_DUE_TO_INTERFERENCE,
			"RAY": conf.RAY, 
			"MINDIST": conf.MINDIST,
			"SIMTIME": conf.SIMTIME,
			"PERIOD": conf.PERIOD,
			"PACKETLENGTH": conf.PACKETLENGTH,  
			"nrMessages": messageSeq
		}
		subdir = "Current"
		simReport(data, subdir, nrNodes)
	print('Collision rate average:', round(np.nanmean(collisionRate), 2))
	print('Reachability average:', round(np.nanmean(nodeReach), 2))
	print('Usefulness average:', round(np.nanmean(nodeUsefulness), 2))
	print('Delay average:', round(np.nanmean(meanDelay), 2))
	print('Tx air utilization average:', round(np.nanmean(meanTxAirUtilization), 2))
	collisions.append(np.nanmean(collisionRate))
	reachability.append(np.nanmean(nodeReach))
	usefulness.append(np.nanmean(nodeUsefulness))
	meanDelays.append(np.nanmean(meanDelay))
	meanTxAirUtils.append(np.nanmean(meanTxAirUtilization))
	collisionStds.append(np.nanstd(collisionRate))
	reachabilityStds.append(np.nanstd(nodeReach))
	usefulnessStds.append(np.nanstd(nodeUsefulness))
	delayStds.append(np.nanstd(meanDelay))
	txAirUtilsStds.append(np.nanstd(meanTxAirUtilization))


plt.errorbar(parameters, collisions, collisionStds, fmt='-o', capsize=3, ecolor='red', elinewidth=0.5, capthick=0.5)
plt.xlabel('#nodes')
plt.ylabel('Collision rate (%)')
plt.figure()
plt.errorbar(parameters, meanDelays, delayStds, fmt='-o', capsize=3, ecolor='red', elinewidth=0.5, capthick=0.5)
plt.xlabel('#nodes')
plt.ylabel('Average delay (ms)')
plt.figure()
plt.errorbar(parameters, meanTxAirUtils, txAirUtilsStds, fmt='-o', capsize=3, ecolor='red', elinewidth=0.5, capthick=0.5)
plt.xlabel('#nodes')
plt.ylabel('Average Tx air utilization (ms)')
plt.figure()
plt.errorbar(parameters, reachability, reachabilityStds, fmt='-o', capsize=3, ecolor='red', elinewidth=0.5, capthick=0.5)
plt.xlabel('#nodes')
plt.ylabel('Reachability (%)')
plt.figure()
plt.errorbar(parameters, usefulness, usefulnessStds, fmt='-o', capsize=3, ecolor='red', elinewidth=0.5, capthick=0.5)
plt.xlabel('#nodes')
plt.ylabel('Usefulness (%)')
plt.show()
