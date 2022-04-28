# Meshtasticator
Discrete-event simulator for layers 0-3 of [Meshtastic](https://meshtastic.org/), to assess the scalability of the protocol. 
The source code is based on [this repo](https://github.com/lucagioacchini/lora-network-simulator), which eventually stems from [1].

## Synopsis
```./loraSim.py <modem (0-6)> [nr_nodes] [--from-file <file_name>]``` 

### Modem 
The modem number is defined as below: 
|Modem  | Name | Bandwidth (kHz) | Coding rate | Spreading Factor
|--|--|--|--|--|
| 0 |Short Fast|250|8|7
| 1 |Short Slow|250|8|8
| 2 |Mid Fast|250|8|9
| 3 |Mid Slow|250|8|10
| 4 |Long Fast|250|8|11
| 5 |Long Slow|125|8|12
| 6 |Very Long Slow|31.25|8|12

### Number of nodes
If number of nodes is specified, the simulation starts with random placement of these nodes. It makes sure that each node can reach at least one other node. Furthermore, all nodes are placed at a configurable minimum distance (MINDIST) from each other. 
If you do not specify the number of nodes, you can place the nodes yourself on a plot. 

There are some other configurations that can be set in *lib/config.py*, which are listed below.

### Model
This feature is referred to the path loss model. The implemented pathloss models are:
* ```0``` set the log-distance model  
* ```1``` set the Okumura-Hata for small and medium-size cities model  
* ```2``` set the Okumura-Hata for metropolitan areas  
* ```3``` set the Okumura-Hata for suburban enviroments  
* ```4``` set the Okumura-Hata for rural areas  
* ```5``` set the 3GPP for suburban macro-cell  
* ```6``` set the 3GPP for metropolitan macro-cell  

### Interference level 
Chance that at a given moment there is already a LoRa packet being sent on your channel, outside of the Meshtastic traffic. Given in a ratio from 0 to 1.

## Example
Run ```loraMesh.py 0 --from-file collision``` to see a simulation of three nodes, in which some packets might collide due to the hidden node problem.

## License
This work is licensed under a [Creative Commons Attribution 4.0 International License](https://creativecommons.org/licenses/by/4.0/). 

## Further Reading
1. [S. Spinsante, L. Gioacchini and L. Scalise, "A novel experimental-based tool for the design of LoRa networks," 2019 II Workshop on Metrology for Industry 4.0 and IoT (MetroInd4.0&IoT), 2019, pp. 317-322, doi: 10.1109/METROI4.2019.8792833.](https://ieeexplore.ieee.org/document/8792833)

