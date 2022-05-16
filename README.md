# Meshtasticator
Discrete-event simulator for layers 0-3 of [Meshtastic](https://meshtastic.org/), to understand its working and assess the scalability of the protocol.
It is currently based on [Meshtastic-device commit a7f4263](https://github.com/meshtastic/Meshtastic-device/tree/a7f4263db41e19c6c8875cd338b0e3a39e2ed074).

The source code is based on [this repo](https://github.com/lucagioacchini/lora-network-simulator), which eventually stems from [1].

## Synopsis
```python3 loraMesh.py [nr_nodes] [--from-file <file_name>]``` 

This runs one simulation, after which it plots the placement of nodes and time schedule for each set of overlapping messages.

![](/img/placement_schedule.png)

If no argument is given, you first have to place the nodes on a plot. 
If the number of nodes is given, it will randomly place nodes in the area. It makes sure that each node can reach at least one other node. Furthermore, all nodes are placed at a configurable minimum distance (MINDIST) from each other. 
If you use the argument --from-file <file_name>, it reads the location of nodes from a file in */out/coords*. Do not specify the number of nodes in this case.

```python3 batchSim.py``` 

This runs multiple repetitions of simulations for a set of parameters defined in the script, e.g. the number of nodes. Afterwards, it plots relevant metrics obtained from the simulations. It saves these metrics in */out/report/* to analyze them later on.

For example, these are the results of 100 simulations of 200s with a different hop limit and number of nodes. As expected, the average number of nodes reached for each generated message increases as the hop limit increases. 

![](/img/reachability_hops.png)

However, it comes at the cost of usefulness, i.e., the amount of received packets that contain a new message (not a duplicate due to rebroadcasting) out of all packets received. 

![](/img/usefulness_hops.png)


## Explanation
A discrete-event simulator jumps from event to event over time, where an event is a change in the state of the system. It is therefore well-suited for simulating communication networks.

For every node in the simulation, an instance is created that mimics the [Meshtastic logic](https://meshtastic.org/docs/developers/firmware/mesh-alg#current-algorithm). Each node runs three processes in parallel: *generateMessage*, *transmit* and *receive*. The first creates an event by constructing a new message with unique sequence number at a random time, taken from an exponential distribution. For now, each generated message is of the same payload size. The second and third processes model the actual transmitting and receiving behavior, respectively. 

The model of the LoRa physical (PHY) layer is in */lib/phy.py*. Depending on the modem used, it is calculated what the airtime of a packet is. The PHY layer uses a configurable pathloss model to estimate whether nodes at a specific distance can sense each other's packets. Furthermore, it determines whether two packets collide, which depends on the frequency, spreading factor, received time and received power of the two packets.  

The routing behavior is implemented in each of the processes of the node. Inside *generateMessage*, reliable retransmissions are handled if no implicit acknowledgement is received. A MeshPacket (defined in */lib/packet.py*) is created to transfer the message. Note that there may be multiple packets created containing the same message, due to retransmissions and rebroadcasting. In *receive*, it is decided what to do on reception of a packet. A packet is flooded if its hoplimit is not zero and no rebroadcast of this packet was heard before. In *transmit*, delays of the Medium Access Control (MAC) layer are called from */lib/mac.py*. The MAC uses a listen-before-talk mechanism, including introducing (random or SNR-based) delays before transmitting a packet. When a packet is ready to be transferred over the air, it is first checked whether in the meantime still no acknowledgement was received, otherwise the transmission is canceled.

The actual communication between processes of different nodes is handled by a BroadcastPipe of [Simpy](https://simpy.readthedocs.io/en/latest/examples/process_communication.html). This ensures that a transmitted packet by one node creates events (one at the start of a packet and one at the end) at the receiving nodes. 

## Configurations
There are some other configurations that can be set in */lib/config.py*, some of which are listed below.

### Modem
The LoRa modem that is used, as defined below:
|Modem  | Name | Bandwidth (kHz) | Coding rate | Spreading Factor
|--|--|--|--|--|
| 0 |Short Fast|250|8|7
| 1 |Short Slow|250|8|8
| 2 |Mid Fast|250|8|9
| 3 |Mid Slow|250|8|10
| 4 |Long Fast|250|8|11
| 5 |Long Slow|125|8|12
| 6 |Very Long Slow|31.25|8|12

### Model
This feature is referred to the path loss model. The implemented pathloss models are:
* ```0``` set the log-distance model  
* ```1``` set the Okumura-Hata for small and medium-size cities model  
* ```2``` set the Okumura-Hata for metropolitan areas  
* ```3``` set the Okumura-Hata for suburban enviroments  
* ```4``` set the Okumura-Hata for rural areas  
* ```5``` set the 3GPP for suburban macro-cell  
* ```6``` set the 3GPP for metropolitan macro-cell  
* ```7``` set the Polynomial 3rd degree 
* ```8``` set the Polynomial 6th degree 

### Period
Mean period (in ms) with which the nodes generate a new message following an exponential distribution. 

### Interference level 
Chance that at a given moment there is already a LoRa packet being sent on your channel, outside of the Meshtastic traffic. Given in a ratio from 0 to 1. 

## License
This work is licensed under a [Creative Commons Attribution 4.0 International License](https://creativecommons.org/licenses/by/4.0/). 

## References
1. [S. Spinsante, L. Gioacchini and L. Scalise, "A novel experimental-based tool for the design of LoRa networks," 2019 II Workshop on Metrology for Industry 4.0 and IoT (MetroInd4.0&IoT), 2019, pp. 317-322, doi: 10.1109/METROI4.2019.8792833.](https://ieeexplore.ieee.org/document/8792833)
2. [Martin C. Bor, Utz Roedig, Thiemo Voigt, and Juan M. Alonso, "Do LoRa Low-Power Wide-Area Networks Scale?", In Proceedings of the 19th ACM International Conference on Modeling, Analysis and Simulation of Wireless and Mobile Systems (MSWiM '16), 2016. Association for Computing Machinery, New York, NY, USA, 59–67.](https://doi.org/10.1145/2988287.2989163)

