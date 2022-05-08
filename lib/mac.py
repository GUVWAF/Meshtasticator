from .phy import airtime, MIN_TX_WAIT_MSEC
from . import config as conf
import random

VERBOSE = False


def setTransmitDelay(node, packet):  # from RadioLibInterface::setTransmitDelay
    for p in reversed(node.packetsAtN[node.nodeid]):
        if p.seq == packet.seq and p.rssiAtN[node.nodeid] != 0 and p.receivedAtN[node.nodeid] == True: 
            # verboseprint('At time', round(self.env.now, 3), 'pick delay with RSSI of node', self.nodeid, 'is', p.rssiAtN[self.nodeid])
            return getTxDelayMsecWeighted(node, p.rssiAtN[node.nodeid])  # weigthed waiting based on RSSI
    return getTxDelayMsec()


def getTxDelayMsecWeighted(node, rssi):  # from RadioInterface::getTxDelayMsecWeighted
    shortPacketMsec = int(airtime(conf.SFMODEM[conf.MODEM], conf.CRMODEM[conf.MODEM], 0, conf.BWMODEM[conf.MODEM]))
    snr = rssi-conf.NOISE_LEVEL
    SNR_MIN = -20
    SNR_MAX = 15
    if snr < SNR_MIN:
        verboseprint('Minimum SNR at RSSI of', rssi, 'dBm')  
        snr = SNR_MIN
    if snr > SNR_MAX:
        verboseprint('Maximum SNR at RSSI of', rssi, 'dBm')  
        snr = SNR_MAX

    if node.isRouter == True:
        minWait = MIN_TX_WAIT_MSEC
        maxWait = MIN_TX_WAIT_MSEC + (shortPacketMsec / 2)
    else:
        minWait = MIN_TX_WAIT_MSEC + (shortPacketMsec / 2)
        maxWait = MIN_TX_WAIT_MSEC + shortPacketMsec * 2

    return int((snr - SNR_MIN) * (maxWait - minWait) / (SNR_MAX - SNR_MIN) + minWait);


def getTxDelayMsec():  # from RadioInterface::getTxDelayMsec
    shortPacketMsec = int(airtime(conf.SFMODEM[conf.MODEM], conf.CRMODEM[conf.MODEM], 0, conf.BWMODEM[conf.MODEM]))
    return random.randint(MIN_TX_WAIT_MSEC, MIN_TX_WAIT_MSEC + shortPacketMsec) 


def getRetransmissionMsec():  # from RadioInterface::getRetransmissionMsec
    shortPacketMsec = int(airtime(conf.SFMODEM[conf.MODEM], conf.CRMODEM[conf.MODEM], 0, conf.BWMODEM[conf.MODEM]))
    return random.randint(9 * shortPacketMsec, 10 * shortPacketMsec)


if VERBOSE:
	def verboseprint(*args, **kwargs): 
		print(*args, **kwargs)
else:   
	def verboseprint(*args, **kwargs): 
		pass