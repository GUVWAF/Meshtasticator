import random
from . import config as conf
from .collision import * 
import math

random.seed(conf.SEED)
MIN_TX_WAIT_MSEC = 100

def getTxDelayMsecWeighted(node, rssi):
    shortPacketMsec = int(airtime(conf.SFMODEM[conf.MODEM], conf.CRMODEM[conf.MODEM], 0, conf.BWMODEM[conf.MODEM]))
    snr = rssi-conf.NOISE_LEVEL
    SNR_MIN = -20
    SNR_MAX = 15

    if node.isRouter == True:
        minWait = MIN_TX_WAIT_MSEC
        maxWait = MIN_TX_WAIT_MSEC + (shortPacketMsec / 2)
    else:
        minWait = MIN_TX_WAIT_MSEC + (shortPacketMsec / 2)
        maxWait = MIN_TX_WAIT_MSEC + shortPacketMsec * 2

    return int((snr - SNR_MIN) * (maxWait - minWait) / (SNR_MAX - SNR_MIN) + minWait);


def getTxDelayMsec():
    shortPacketMsec = int(airtime(conf.SFMODEM[conf.MODEM], conf.CRMODEM[conf.MODEM], 0, conf.BWMODEM[conf.MODEM]))
    return random.randint(MIN_TX_WAIT_MSEC, MIN_TX_WAIT_MSEC + shortPacketMsec) 


def isChannelActive(node, env):
    if random.randrange(10) <= conf.INTERFERENCE_LEVEL*10:
        return True
    for p in node.packetsAtN[node.nodeid]:
        if p.sensedByN[node.nodeid]:
            if env.now >= p.addTime and env.now <= p.addTime+p.recTime:
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
