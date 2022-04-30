import numpy as np

MODEM = 0
MODEL = 5
NR_NODES = 10
INTERFERENCE_LEVEL = 0.05
COLLISION_DUE_TO_INTERFERENCE = False
RAY = 3000  # m 
MINDIST = 5
SIMTIME = 200000  # ms
PERIOD = 100000  # mean period of generating a new message with exponential distribution in ms
PACKETLENGTH = 50 
NOISE_LEVEL = -119.25  # some noise level in dB, based on SNR_MIN and minimum receiver sensitivity
OX = 0.0  # origin x-coordinate
OY = 0.0  # origin y-coordinate
GAMMA = 2.08  # PHY parameter
D0 = 40.0  # PHY parameter
LPLD0 = 127.41  # PHY parameter
NPREAM = 32   # number of preamble symbols from RadioInterface.h 
GL = 0	# antenna gain in dB
HM = 1.0  # height of the mobile device in m
SEED = 12
VERBOSE = True
RANDOM = False

xs = []
ys = []

# Meshtastic 
maxRetransmission = 3
hopLimit = 1

# from RadioInterface.cpp RegionInfo regions[]
regions = { "US": {"freq_start": 902e6, "freq_end": 928e6, "power_limit": 30},
            "EU433": {"freq_start": 433e6, "freq_end": 434e6, "power_limit": 12}, 
            "EU868": {"freq_start": 868e6, "freq_end": 868e6, "power_limit": 16}}

REGION = regions["EU868"]
PTX = REGION["power_limit"]

# from RadioInterface::applyModemConfig() 
BWMODEM = np.array([250e3, 250e3, 250e3, 250e3, 250e3, 125e3, 31.25e3])  # bandwidth
SFMODEM = np.array([7, 8, 9, 10, 11, 12, 12]) # spreading factor
CRMODEM = np.array([8, 8, 8, 8, 8, 8, 8]) # coding rate
# minimum sensitivity from [2], Table 3 (Very Long Slow is an extrapolation)
SENSMODEM = np.array([-124.25, -126.75, -128.25, -130.25, -132.75, -133.25, -139.25])
