import numpy as np
from . import config as conf
from .channel import *
import random

random.seed(conf.SEED)

class MeshPacket(): 
	def __init__(self, x, y, tx_nodeId, plen, prio, seq):
		self.addTime = 0
		self.tx_nodeId = tx_nodeId
		self.txpow = conf.PTX
		self.LplAtN = [0 for _ in range(conf.NR_NODES)]
		self.rssiAtN = [0 for _ in range(conf.NR_NODES)]
		self.sensedByN = [False for _ in range(conf.NR_NODES)]
		self.collidedAtN = [False for _ in range(conf.NR_NODES)]
		self.receivedAtN = [False for _ in range(conf.NR_NODES)]

		self.prio = prio
		self.seq = seq

		# configuration values
		self.sf = conf.SFMODEM[conf.MODEM]
		self.cr =  conf.CRMODEM[conf.MODEM]
		self.bw =  conf.BWMODEM[conf.MODEM]
		self.freq =  conf.REGION["freq_start"]

		for rx_node in conf.nodes:
			if rx_node.nodeid == self.tx_nodeId:
				continue
			dist_2d = np.sqrt((x-rx_node.x)*(x-rx_node.x)+(y-rx_node.y)*(y-rx_node.y))
			self.LplAtN[rx_node.nodeid] = estimatePathLoss(dist_2d, self.freq)
			self.rssiAtN[rx_node.nodeid] = self.txpow + conf.GL - self.LplAtN[rx_node.nodeid]
			if self.rssiAtN[rx_node.nodeid] >= conf.SENSMODEM[conf.MODEM]:
				self.sensedByN[rx_node.nodeid] = True
				
		self.packetlen = plen
		self.recTime = airtime(self.sf, self.cr, self.packetlen, self.bw)
