import random
from . import config as conf
import math

VERBOSE = False
random.seed(conf.SEED)
#                           CAD duration   +     airPropagationTime+TxRxTurnaround+MACprocessing
slotTime = 8.5 * (2.0**conf.SFMODEM[conf.MODEM])/conf.BWMODEM[conf.MODEM]*1000 + 0.2 + 0.4 + 7


def checkcollision(env, packet, rx_nodeId, packetsAtN):
	# Check for collisions at rx_node
	col = 0
	if conf.COLLISION_DUE_TO_INTERFERENCE:
		if random.randrange(10) <= conf.INTERFERENCE_LEVEL*10:
			packet.collidedAtN[rx_nodeId] = True

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


def isChannelActive(node, env):
    if random.randrange(10) <= conf.INTERFERENCE_LEVEL*10:
        return True
    for p in node.packets:
        if p.detectedByN[node.nodeid]: 
            # You will miss detecting a packet if it has just started before you could do CAD
            if env.now >= p.startTime+slotTime and env.now <= p.endTime:
                return True
    return False


def airtime(sf, cr, pl, bw):
    H = 0		# implicit header disabled (H=0) or not (H=1)
    DE = 0	   # low data rate optimization enabled (=1) or not (=0)

    if bw == 125 and sf in [11, 12]: # low data rate optimization 
        DE = 1
    if sf == 6: # can only have implicit header with SF6
        H = 1

    Tsym = (2.0**sf)/bw
    Tpream = (conf.NPREAM + 4.25)*Tsym
    payloadSymbNB = 8 + max(math.ceil((8.0*pl-4.0*sf+28+16-20*H)/(4.0*(sf-2*DE)))*(cr+4), 0)
    Tpayload = payloadSymbNB * Tsym
    
    return (Tpream + Tpayload)*1000


def estimatePathLoss(dist, freq):	
    # Log-Distance model
    if conf.MODEL == 0: 
        Lpl = conf.LPLD0 + 10*conf.GAMMA*math.log10(dist/conf.D0)
            
    # Okumura-Hata model
    elif conf.MODEL >= 1 and conf.MODEL <= 4:
        #small and medium-size cities
        if conf.MODEL == 1:
            ahm = (1.1*(math.log10(freq)-math.log10(1000000))-0.7)*conf.HM \
            - (1.56*(math.log10(freq)-math.log10(1000000))-0.8)
            
            C = 0 
        #metropolitan areas
        elif conf.MODEL == 2:
            if (freq <= 200000000):
                ahm = 8.29*((math.log10(1.54*conf.HM))**2) - 1.1
            elif (freq >= 400000000):
                ahm = 3.2*((math.log10(11.75*conf.HM))**2) - 4.97
            C = 0
        #suburban enviroments
        elif conf.MODEL == 3:
            ahm = (1.1*(math.log10(freq)-math.log10(1000000))-0.7)*conf.HM \
            - (1.56*(math.log10(freq)-math.log10(1000000))-0.8)
            
            C = -2*((math.log10(freq)-math.log10(28000000))**2) - 5.4
        #rural area
        elif conf.MODEL == 4:
            ahm = (1.1*(math.log10(freq)-math.log10(1000000))-0.7)*conf.HM \
            - (1.56*(math.log10(freq)-math.log10(1000000))-0.8)
            
            C = -4.78*((math.log10(freq)-math.log10(1000000))**2) \
            +18.33*(math.log10(freq)-math.log10(1000000)) - 40.98
            
        A = 69.55 + 26.16*(math.log10(freq)-math.log10(1000000)) \
        - 13.82*math.log(conf.HM) - ahm
        
        B = 44.9-6.55*math.log10(conf.HM)

        Lpl = A + B*(math.log10(dist)-math.log10(1000)) + C		
        
    # 3GPP model
    elif conf.MODEL >= 5 and conf.MODEL < 7:
        # Suburban Macro
        if conf.MODEL == 5:
            C = 0  # dB
        # Urban Macro
        elif conf.MODEL == 6:
            C = 3 #dB
            
        Lpl = (44.9-6.55*math.log10(conf.HM))*(math.log10(dist) - math.log10(1000)) \
        + 45.5 + (35.46-1.1*conf.HM)*(math.log10(freq)-math.log10(1000000)) \
        - 13.82*math.log10(conf.HM)+0.7*conf.HM+C
    
    # Polynomial 3rd degree
    elif conf.MODEL == 7:
        p1 = -5.491e-06
        p2 = 0.002936
        p3 = -0.5004
        p4 = -70.57
        
        Lpl = p1*math.pow(dist, 3) + p2*math.pow(dist, 2) \
        + p3*dist + p4
    
    # Polynomial 6th degree
    elif conf.MODEL == 8:
        p1 = 3.69e-12
        p2 = 5.997e-11 
        p3 = -1.381e-06 
        p4 = 0.0005134 
        p5 = -0.07318 
        p6 = 4.254 
        p7 = -171  
    
        Lpl = p1*math.pow(dist, 6) + p2*math.pow(dist, 5) \
        + p3*math.pow(dist, 4) + p4*math.pow(dist, 3) \
        + p5*math.pow(dist, 2) + p6*dist + p7
        
    return Lpl


if VERBOSE:
	def verboseprint(*args, **kwargs): 
		print(*args, **kwargs)
else:   
	def verboseprint(*args, **kwargs): 
		pass