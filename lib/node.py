from . import config as conf
from .packet import *
from .common import *
from .collision import *
from .channel import isChannelActive
import random
import math
import simpy

random.seed(conf.SEED)


class MeshNode():
	def __init__(self, env, bc_pipe, nodeid, period, messages, packetsAtN, packets, x=-1, y=-1):
		self.nodeid = nodeid
		self.x = x
		self.y = y
		self.packetQueue = []
		self.env = env
		self.period = period
		self.bc_pipe = bc_pipe
		self.rx_snr = 0
		self.isRouter = False
		self.messages = messages
		self.packetsAtN = packetsAtN
		self.nrPacketsSent = 0
		self.packets = packets
		self.leastReceivedHopLimit = {}
		self.isReceiving = False
		self.isTransmitting = False

		if x == -1 and y == -1: 
			found = False
			while not found:
				a = random.random()
				b = random.random()
				if b < a:
					a,b = b,a
				posx = b*conf.RAY*math.cos(2*math.pi*a/b)+conf.OX
				posy = b*conf.RAY*math.sin(2*math.pi*a/b)+conf.OY
				if len(conf.nodes) > 0:
					for n in conf.nodes:
						dist = np.sqrt(((abs(n.x-posx))**2)+((abs(n.y-posy))**2))
						if dist >= 10:
							found = 1
							self.x = posx
							self.y = posy
				else:
					self.x = posx
					self.y = posy
					found = True

		env.process(self.generateMessage())
		env.process(self.receive(self.bc_pipe.get_output_conn()))
		self.transmitter = simpy.Resource(env, 1)


	def generateMessage(self):
		while True:	
			nextGen = random.expovariate(1.0/float(self.period))
			if self.env.now+nextGen+conf.hopLimit*airtime(conf.SFMODEM[conf.MODEM], conf.CRMODEM[conf.MODEM], conf.packetLength, conf.BWMODEM[conf.MODEM]) < conf.SIMTIME:
				yield self.env.timeout(nextGen) 
				conf.packetSeq += 1
				self.messages.append(MeshMessage(self.nodeid, self.env.now, conf.packetSeq))
				p = MeshPacket(self.nodeid, self.nodeid, self.x, self.y, conf.packetLength, conf.packetSeq)  
				verboseprint('At time', round(self.env.now, 3), 'node', self.nodeid, 'generated message', p.seq)
				self.packets.append(p)
				self.env.process(self.transmit(p))
				while True: # check if received ACK (ReliableRouter)
					retransmissionMsec = getRetransmissionMsec() 
					yield self.env.timeout(retransmissionMsec)
					ackReceived = False  # check whether you received an ACK on any of your transmitted packets 
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
							pNew = MeshPacket(self.nodeid, self.nodeid, self.x, self.y, conf.packetLength, p.seq)  
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
			txTime = self.setRandomDelay(packet) 
			verboseprint('At time', round(self.env.now, 3), 'node', self.nodeid, 'picked wait time', txTime)
			yield self.env.timeout(txTime)

			# wait when currently receiving or transmitting, or channel is active
			while self.isReceiving or self.isTransmitting or isChannelActive(self, self.env):
				# verboseprint('Busy tx/rx or channel busy')
				txTime = self.setRandomDelay(packet) 
				yield self.env.timeout(txTime)
			verboseprint('At time', round(self.env.now, 3), 'node', self.nodeid, 'ends waiting')	

			if packet.seq not in self.leastReceivedHopLimit:
				self.leastReceivedHopLimit[packet.seq] = packet.hopLimit+1 
			if self.leastReceivedHopLimit[packet.seq] > packet.hopLimit: 
				verboseprint('At time', round(self.env.now, 3), 'node', self.nodeid, 'started low level send', packet.seq, 'hopLimit', packet.hopLimit, 'original Tx', packet.origTxNodeId)
				self.nrPacketsSent += 1
				for rx_node in conf.nodes:
					if packet.sensedByN[rx_node.nodeid] == True:
						if (checkcollision(self.env, packet, rx_node.nodeid, self.packetsAtN) == 0):
							self.packetsAtN[rx_node.nodeid].append(packet)
				packet.startTime = self.env.now
				packet.endTime = self.env.now + packet.timeOnAir
				self.bc_pipe.put(packet)
				self.isTransmitting = True
				yield self.env.timeout(packet.timeOnAir)
				self.isTransmitting = False
			else: 
				# received ACK: abort transmit, remove from packets generated 
				verboseprint('At time', round(self.env.now, 3), 'node', self.nodeid, 'in the meantime received ACK, abort packet with seq. nr', packet.seq)
				self.packets.remove(packet)


	def receive(self, in_pipe):
		while True:
			p = yield in_pipe.get()
			if p.sensedByN[self.nodeid] and p.onAirToN[self.nodeid]:
				verboseprint('At time', round(self.env.now, 3), 'node', self.nodeid, 'started receiving packet', p.seq, 'from', p.txNodeId)
				p.onAirToN[self.nodeid] = False 
				self.isReceiving = True
			else:
				if p.sensedByN[self.nodeid]:
					self.isReceiving = False
					if p.collidedAtN[self.nodeid]:
						verboseprint('At time', round(self.env.now, 3), 'node', self.nodeid, 'could not decode packet.')
						continue
					p.receivedAtN[self.nodeid] = True
					verboseprint('At time', round(self.env.now, 3), 'node', self.nodeid, 'received packet', p.seq)
					
					# Rebroadcasting received message (FloodingRouter)
					if p.seq not in self.leastReceivedHopLimit:  # did not yet receive packet with this seq nr.
						if p.origTxNodeId != self.nodeid:
							# verboseprint('Node', self.nodeid, 'received packet nr.', p.seq, 'orig. Tx', p.origTxNodeId)
							conf.usefulPackets += 1
						self.leastReceivedHopLimit[p.seq] = p.hopLimit
					# else:
					# 	verboseprint('Node', self.nodeid, 'ALREADY received packet nr.', p.seq)
					if p.hopLimit < self.leastReceivedHopLimit[p.seq]:  # hop limit of received packet is lower than previously received one
						self.leastReceivedHopLimit[p.seq] = p.hopLimit	

					if p.origTxNodeId == self.nodeid: 
						# verboseprint("Node", self.nodeid, 'received own generated message.')
						p.ackReceived = True
						continue
					
					ackReceived = False		
					for sentPacket in self.packets:
						if sentPacket.txNodeId == self.nodeid and sentPacket.seq == p.seq:
							ackReceived = True
							sentPacket.ackReceived = True
							
					if not ackReceived and p.hopLimit > 0:
						pNew = MeshPacket(p.origTxNodeId, self.nodeid, self.x, self.y, conf.packetLength, p.seq) 
						pNew.hopLimit = p.hopLimit-1
						self.packets.append(pNew)
						self.env.process(self.transmit(pNew))


	def setRandomDelay(self, packet):
		for p in reversed(self.packetsAtN[self.nodeid]):
				if p.seq == packet.seq and p.rssiAtN[self.nodeid] != 0: 
					# verboseprint('At time', round(self.env.now, 3), 'pick delay with RSSI of node', self.nodeid, 'is', p.rssiAtN[self.nodeid])
					return getTxDelayMsecWeighted(self, p.rssiAtN[self.nodeid])  # weigthed waiting based on RSSI
		return getTxDelayMsec()

		
