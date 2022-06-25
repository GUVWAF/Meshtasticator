from .phy import airtime, slotTime
from . import config as conf
import random

VERBOSE = False
CWmin = 2
CWmax = 8
PROCESSING_TIME_MSEC = 4500


def setTransmitDelay(node, packet):  # from RadioLibInterface::setTransmitDelay
    for p in reversed(node.packetsAtN[node.nodeid]):
        if p.seq == packet.seq and p.rssiAtN[node.nodeid] != 0 and p.receivedAtN[node.nodeid] == True: 
            # verboseprint('At time', round(self.env.now, 3), 'pick delay with RSSI of node', self.nodeid, 'is', p.rssiAtN[self.nodeid])
            return getTxDelayMsecWeighted(node, p.rssiAtN[node.nodeid])  # weigthed waiting based on RSSI
    return getTxDelayMsec(node)


def getTxDelayMsecWeighted(node, rssi):  # from RadioInterface::getTxDelayMsecWeighted
    snr = rssi-conf.NOISE_LEVEL
    SNR_MIN = -20
    SNR_MAX = 15
    if snr < SNR_MIN:
        verboseprint('Minimum SNR at RSSI of', rssi, 'dBm')  
        snr = SNR_MIN
    if snr > SNR_MAX:
        verboseprint('Maximum SNR at RSSI of', rssi, 'dBm')  
        snr = SNR_MAX

    CWsize = int((snr - SNR_MIN) * (CWmax - CWmin) / (SNR_MAX - SNR_MIN) + CWmin)
    if node.isRouter == True:
        CW = random.randint(0, 2*CWsize-1)
    else:
        CW = random.randint(0, 2**CWsize-1)
    verboseprint('Node', node.nodeid, 'has CW size', CWsize, 'and picked CW', CW)
    return CW * slotTime


def getTxDelayMsec(node):  # from RadioInterface::getTxDelayMsec
    channelUtil = node.airUtilization/node.env.now*100 
    CWsize = int(channelUtil*(CWmax - CWmin)/100 + CWmin)
    CW = random.randint(0, 2**CWsize-1)
    verboseprint('Current channel utilization is', channelUtil, 'So picked CW', CW)
    return CW * slotTime


def getRetransmissionMsec(node, packet):  # from RadioInterface::getRetransmissionMsec
    packetAirtime = int(airtime(conf.SFMODEM[conf.MODEM], conf.CRMODEM[conf.MODEM], packet.packetlen, conf.BWMODEM[conf.MODEM]))
    channelUtil = node.airUtilization/node.env.now*100 
    CWsize = int(channelUtil*(CWmax - CWmin)/100 + CWmin)
    return 2*packetAirtime + (2**CWsize + 2**(int((CWmax+CWmin)/2))) * slotTime + PROCESSING_TIME_MSEC;


if VERBOSE:
	def verboseprint(*args, **kwargs): 
		print(*args, **kwargs)
else:   
	def verboseprint(*args, **kwargs): 
		pass
