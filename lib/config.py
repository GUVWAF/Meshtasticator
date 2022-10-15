import numpy as np

MODEL = 5  # Pathloss model to use (see README)

XSIZE = 3000  # horizontal size of the area to simulate in m 
YSIZE = 3000  # vertical size of the area to simulate in m
OX = 0.0  # origin x-coordinate
OY = 0.0  # origin y-coordinate
MINDIST = 10  # minimum distance between each node in the area in m

GL = 0	# antenna gain of each node in dB
HM = 1.0  # height of each node in m

### Meshtastic specific ###
maxRetransmission = 3  # default 3
hopLimit = 3  # default 3
### End of Meshtastic specific ###

### Discrete-event specific ###
MODEM = 4  # LoRa modem to use: 0 = ShortFast, 1 = Short Slow, ... 6 = Very Long Slow
PERIOD = 100000  # mean period of generating a new message with exponential distribution in ms
PACKETLENGTH = 40  # payload in bytes  
SIMTIME = 200000  # duration of one simulation in ms 
INTERFERENCE_LEVEL = 0.05  # chance that at a given moment there is already a LoRa packet being sent on your channel, 
                           # outside of the Meshtastic traffic. Given in a ratio from 0 to 1.  
COLLISION_DUE_TO_INTERFERENCE = False
# from RadioInterface.cpp RegionInfo regions[]
regions = { "US": {"freq_start": 902e6, "freq_end": 928e6, "power_limit": 30},
            "EU433": {"freq_start": 433e6, "freq_end": 434e6, "power_limit": 12}, 
            "EU868": {"freq_start": 868e6, "freq_end": 868e6, "power_limit": 16}}
REGION = regions["US"] # Select a different region here
CHANNEL_NUM = 27  # Channel number 
### End of discrete-event specific ###

### PHY parameters (normally no change needed) ###
PTX = REGION["power_limit"]
# from RadioInterface::applyModemConfig() 
BWMODEM = np.array([250e3, 250e3, 250e3, 250e3, 250e3, 125e3, 31.25e3])  # bandwidth
SFMODEM = np.array([7, 8, 9, 10, 11, 12, 12]) # spreading factor
CRMODEM = np.array([8, 8, 8, 8, 8, 8, 8]) # coding rate
# minimum sensitivity from [2], Table 3 (Very Long Slow is an extrapolation)
SENSMODEM = np.array([-124.25, -126.75, -128.25, -130.25, -132.75, -133.25, -139.25])
# minimum received power for CAD (estimated based on SX126x datasheet)
CADMODEM = np.array([-125, -128, -133, -134, -139, -139, -144])
FREQ = REGION["freq_start"]+BWMODEM[MODEM]*CHANNEL_NUM
NOISE_LEVEL = -119.25  # some noise level in dB, based on SNR_MIN and minimum receiver sensitivity
GAMMA = 2.08  # PHY parameter
D0 = 40.0  # PHY parameter
LPLD0 = 127.41  # PHY parameter
NPREAM = 32   # number of preamble symbols from RadioInterface.h 
### End of PHY parameters ###

# Misc
SEED = 44  # random seed to use
PLOT = True
RANDOM = False
# End of misc

# Initializers
xs = []
ys = []
NR_NODES = []
# End of initializers 
