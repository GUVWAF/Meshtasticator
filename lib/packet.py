import numpy as np
from . import config as conf
from .phy import *
import random

random.seed(conf.SEED)

class MeshPacket(): 
	def __init__(self, nodes, origTxNodeId, txNodeId, x, y, plen, seq):
		self.origTxNodeId = origTxNodeId
		self.txNodeId = txNodeId
		self.txpow = conf.PTX
		self.LplAtN = [0 for _ in range(conf.NR_NODES)]
		self.rssiAtN = [0 for _ in range(conf.NR_NODES)]
		self.sensedByN = [False for _ in range(conf.NR_NODES)]
		self.collidedAtN = [False for _ in range(conf.NR_NODES)]
		self.receivedAtN = [False for _ in range(conf.NR_NODES)]
		self.onAirToN = [True for _ in range(conf.NR_NODES)]
		self.seq = seq

		# configuration values
		self.sf = conf.SFMODEM[conf.MODEM]
		self.cr = conf.CRMODEM[conf.MODEM]
		self.bw = conf.BWMODEM[conf.MODEM]
		self.freq = conf.REGION["freq_start"]

		for rx_node in nodes:
			if rx_node.nodeid == self.txNodeId:
				continue
			dist_2d = np.sqrt((x-rx_node.x)*(x-rx_node.x)+(y-rx_node.y)*(y-rx_node.y))
			self.LplAtN[rx_node.nodeid] = estimatePathLoss(dist_2d, self.freq)
			self.rssiAtN[rx_node.nodeid] = self.txpow + conf.GL - self.LplAtN[rx_node.nodeid]
			if self.rssiAtN[rx_node.nodeid] >= conf.SENSMODEM[conf.MODEM]:
				self.sensedByN[rx_node.nodeid] = True
				
		self.packetlen = plen
		self.timeOnAir = airtime(self.sf, self.cr, self.packetlen, self.bw)
		self.startTime = 0
		self.endTime = 0

		# Routing
		self.retransmissions = conf.maxRetransmission
		self.ackReceived = False
		self.hopLimit = conf.hopLimit


class MeshMessage():
	def __init__(self, origTxNodeId, genTime, seq):
		self.origTxNodeId = origTxNodeId
		self.genTime = genTime
		self.seq = seq
		self.endTime = 0