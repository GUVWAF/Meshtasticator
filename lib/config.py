import numpy as np

MODEM = 0
RANDOM = False
INTERFERENCE_LEVEL = 0.2
MODEL = 5
NR_NODES = 0
RAY = 1000  # m 
SIMTIME = 200000  # ms
OX = 0.0  # origin x-coordinate
OY = 0.0  # origin y-coordinate
GAMMA = 2.08
D0 = 40.0
LPLD0 = 127.41
NPREAM = 32   # number of preamble symbols from RadioInterface.h 
GL = 0	# antenna gain in dB
HM = 1.0  # height of the mobile device in m
NOISE_LEVEL = -100  # some noise level in dB
SEED = 89

# simulation variables 
packetSeq = 0 
nodes = []
usefulPackets = 0
xs = []
ys = []

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
# minimum sensitivity from [1], Table 3 (VLongSlow is extrapolation)
SENSMODEM = np.array([-124.25, -126.75, -128.25, -130.25, -132.75, -133.25, -139.25])

# Meshtastic 
maxRetransmission = 3
hopLimit = 3
packetLength = 100 
