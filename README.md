# Meshtasticator
Discrete-event simulator for layers 0-3 of [Meshtastic](https://meshtastic.org/), to assess the scalability of the protocol. 
The source code is based on [this repo](https://github.com/lucagioacchini/lora-network-simulator), which eventually stems from [1].

## Synopsis
```./loraSim.py <number of nodes> <model>```

### Model
This feature is referred to the path loss model. The implemented pathloss models are:
* ```0``` set the log-distance model  
* ```1``` set the Okumura-Hata for small and medium-size cities model  
* ```2``` set the Okumura-Hata for metropolitan areas  
* ```3``` set the Okumura-Hata for suburban enviroments  
* ```4``` set the Okumura-Hata for rural areas  
* ```5``` set the 3GPP for suburban macro-cell  
* ```6``` set the 3GPP for metropolitan macro-cell  

## Further Reading
1. [S. Spinsante, L. Gioacchini and L. Scalise, "A novel experimental-based tool for the design of LoRa networks," 2019 II Workshop on Metrology for Industry 4.0 and IoT (MetroInd4.0&IoT), 2019, pp. 317-322, doi: 10.1109/METROI4.2019.8792833.](https://ieeexplore.ieee.org/document/8792833)

