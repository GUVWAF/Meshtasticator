import numpy as np

MODEM = 0
RANDOM = False
INTERFERENCE_LEVEL = 0.2
FULL_COLLISION = True
MODEL = 5
NR_NODES = 0
RAY = 250.0
SIMTIME = 50000  # ms
OX = 0.0  # origin x-coordinate
OY = 0.0  # origin y-coordinate
GAMMA = 2.08
D0 = 40.0
LPLD0 = 127.41
NPREAM = 32   # number of preamble symbols from RadioInterface.h 
GL = 0	# antenna gain in dB
HM = 1.0  # height of the mobile device in m
SEED = 21

nodes = []

# from RadioInterface.cpp RegionInfo regions[]
regions = { "US": {"freq_start": 902, "freq_end": 928, "power_limit": 30},
            "EU433": {"freq_start": 433, "freq_end": 434, "power_limit": 12}, 
            "EU868": {"freq_start": 433, "freq_end": 434, "power_limit": 16}}

REGION = regions["EU433"]
PTX = REGION["power_limit"]

# from RadioInterface::applyModemConfig() 
BWMODEM = np.array([250, 250, 250, 250, 250, 125, 31.25])  # bandwidth
SFMODEM = np.array([7, 8, 9, 10, 11, 12, 12]) # spreading factor
CRMODEM = np.array([8, 8, 8, 8, 8, 8, 8]) # coding rate
# minimum sensitivity from paper, Table 3 (VLongSlow is extrapolation)
SENSMODEM = np.array([-124.25, -126.75, -128.25, -130.25, -132.75, -133.25, -139.25])
