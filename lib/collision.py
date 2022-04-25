from . import config as conf
from .common import verboseprint
import random

def checkcollision(env, packet, rx_nodeId, packetsAtN):
	# Check for collisions at rx_node
	col = 0
	# if random.randrange(10) <= conf.INTERFERENCE_LEVEL*10:
	# 	packet.collidedAtN[rx_nodeId] = True

	if packetsAtN[rx_nodeId]:
		for other in packetsAtN[rx_nodeId]:
			if frequencyCollision(packet, other) and sfCollision(packet, other):
					if timingCollision(env, packet, other):
						verboseprint('Packet nr.', packet.seq, 'from', packet.txNodeId, 'and packet nr.', other.seq, 'from', other.txNodeId, 'will collide!')
						c = powerCollision(packet, other, rx_nodeId)
							# mark all the collided packets
						for p in c:
							p.collidedAtN[rx_nodeId] = True
							if p == packet:
								col = 1
					else:
						pass # no timing collision
		return col
	return 0


def frequencyCollision(p1, p2):
	if (abs(p1.freq-p2.freq)<=120 and (p1.bw==500 or p2.freq==500)):
		return True
	elif (abs(p1.freq-p2.freq)<=60 and (p1.bw==250 or p2.freq==250)):
		return True
	else:
		if (abs(p1.freq-p2.freq)<=30):
			return True
	return False


def sfCollision(p1, p2):
	if p1.sf == p2.sf:
		return True
	return False


def powerCollision(p1, p2, rx_nodeId):
	powerThreshold = 6 # dB
	if abs(p1.rssiAtN[rx_nodeId]  - p2.rssiAtN[rx_nodeId]) < powerThreshold:
		# packets are too close to each other, both collide
		# return both packets as casualties
		return (p1, p2)
	elif p1.rssiAtN[rx_nodeId] - p2.rssiAtN[rx_nodeId] < powerThreshold:
		# p2 overpowered p1, return p1 as casualty
		return (p1,)
	# p2 was the weaker packet, return it as a casualty
	return (p2,)


def timingCollision(env, p1, p2):
	""" assuming p1 is the freshly arrived packet and this is the last check
		we've already determined that p1 is a weak packet, so the only
		way we can win is by being late enough (only the first n - 5 preamble symbols overlap)
	"""
	Tpreamb = 2**p1.sf/(1.0*p1.bw) * (conf.NPREAM - 5)
	p1_cs = env.now + Tpreamb
	if p1_cs < p2.endTime: # p1 collided with p2 and lost
		return True
	return False
