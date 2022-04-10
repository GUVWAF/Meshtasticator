from . import config as conf
from .packet import *
from .common import *
from .collision import *
from .channel import *
import random
import math

random.seed(conf.SEED)


class MeshNode():
	def __init__(self, env, bc_pipe, nodeid, period, packetsAtN, packets, packetSeq):
		self.nodeid = nodeid
		self.x = 0
		self.y = 0
		self.packetQueue = []
		self.env = env
		self.period = period
		self.bc_pipe = bc_pipe
		self.rx_snr = 0
		self.isRouter = False
		self.packetsAtN = packetsAtN
		self.nrPacketsSent = 0
		self.packets = packets
		self.packetSeq = packetSeq

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

		env.process(self.transmit())
		env.process(self.receive(self.bc_pipe.get_output_conn()))


	def transmit(self):
		# listen-before-talk from src/mesh/RadioLibInterface.cpp 
		while True:	
			nextGen = random.expovariate(1.0/float(self.period))
			if self.env.now+nextGen+airtime(conf.SFMODEM[conf.MODEM], conf.CRMODEM[conf.MODEM], 100, conf.BWMODEM[conf.MODEM]) < conf.SIMTIME:
				yield self.env.timeout(nextGen) 
				self.packetSeq += 1
				p = MeshPacket(self.x, self.y, self.nodeid, 100, 1, self.packetSeq)  # packetlen and prio
				self.packets.append(p)

				if channelIsBusy(): 
					self.txTime = getTxDelayMsecWeighted(self, self.rx_snr) 
				else: 
					self.txTime = getTxDelayMsec()
				yield self.env.timeout(self.txTime)
				print('At time', self.env.now, 'node', self.nodeid, 'transmitted packet', p.seq)
				self.nrPacketsSent += 1
				p.addTime = self.env.now

				for rx_node in conf.nodes:
					if p.sensedByN[rx_node.nodeid] == True:
						if (checkcollision(self.env, p, rx_node.nodeid, self.packetsAtN) == 0):
							self.packetsAtN[rx_node.nodeid].append(p)

				self.bc_pipe.put(p)
			else:
				break

        # https://meshtastic.org/docs/developers/firmware/mesh-alg 		


	def receive(self, in_pipe):
		while True:
			p = yield in_pipe.get()
			if p.sensedByN[self.nodeid] and not p.collidedAtN[self.nodeid]:
				p.receivedAtN[self.nodeid] = True
				print('At time', self.env.now, 'node', self.nodeid, 'received packet', p.seq)
		
