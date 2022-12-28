import numpy as np
from lib.common import calcDist
from . import config as conf
from .phy import *
import random

NODENUM_BROADCAST = 0xFFFFFFFF
random.seed(conf.SEED)

class MeshPacket(): 
	def __init__(self, nodes, origTxNodeId, destId, txNodeId, x, y, plen, seq, genTime, wantAck, isAck, requestId):
		self.origTxNodeId = origTxNodeId
		self.destId = destId
		self.txNodeId = txNodeId
		self.wantAck = wantAck
		self.isAck = isAck
		self.seq = seq
		self.requestId = requestId
		self.genTime = genTime
		self.txpow = conf.PTX
		self.LplAtN = [0 for _ in range(conf.NR_NODES)]
		self.rssiAtN = [0 for _ in range(conf.NR_NODES)]
		self.sensedByN = [False for _ in range(conf.NR_NODES)]
		self.detectedByN = [False for _ in range(conf.NR_NODES)]
		self.collidedAtN = [False for _ in range(conf.NR_NODES)]
		self.receivedAtN = [False for _ in range(conf.NR_NODES)]
		self.onAirToN = [True for _ in range(conf.NR_NODES)]

		# configuration values
		self.sf = conf.SFMODEM[conf.MODEM]
		self.cr = conf.CRMODEM[conf.MODEM]
		self.bw = conf.BWMODEM[conf.MODEM]
		self.freq = conf.FREQ
		for rx_node in nodes:
			if rx_node.nodeid == self.txNodeId:
				continue
			dist_2d = calcDist(x, y, rx_node.x, rx_node.y) # np.sqrt((x-rx_node.x)*(x-rx_node.x)+(y-rx_node.y)*(y-rx_node.y))
			self.LplAtN[rx_node.nodeid] = estimatePathLoss(dist_2d, self.freq)
			self.rssiAtN[rx_node.nodeid] = self.txpow + conf.GL - self.LplAtN[rx_node.nodeid]
			if self.rssiAtN[rx_node.nodeid] >= conf.SENSMODEM[conf.MODEM]:
				self.sensedByN[rx_node.nodeid] = True
			if self.rssiAtN[rx_node.nodeid] >= conf.CADMODEM[conf.MODEM]:
				self.detectedByN[rx_node.nodeid] = True
				
		self.packetlen = plen
		self.timeOnAir = airtime(self.sf, self.cr, self.packetlen, self.bw)
		self.startTime = 0
		self.endTime = 0

		# Routing
		self.retransmissions = conf.maxRetransmission
		self.ackReceived = False
		self.hopLimit = conf.hopLimit  # TODO use config of node


class MeshMessage():
	def __init__(self, origTxNodeId, destId, genTime, seq):
		self.origTxNodeId = origTxNodeId
		self.destId = destId
		self.genTime = genTime
		self.seq = seq
		self.endTime = 0
