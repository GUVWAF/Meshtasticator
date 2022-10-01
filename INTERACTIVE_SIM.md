# Interactive Simulator (Work-In-Progress)

The Python script *interactiveSim.py* uses the [Linux native application of Meshtastic](https://meshtastic.org/docs/software/other/docker) in order to simulate multiple instances of the device software. They will communicate using TCP via this script as if they did using their LoRa chip. Currently it will forward a message from a node to all other nodes, thus assuming all nodes are in range of each other. In the future it should calculate which nodes will receive the packet based on their simulated positions and collisions with other packets. 

## Usage
The script requires the [Meshtastic API](https://meshtastic.org/docs/software/python/python-installation). 
The Python script should be run as follows: 

```python3 interactiveSim.py <nrNodes> [--p <full-path-to-program>]```,

where nrNodes is the number of instances you want to launch. Note that for each instance a terminal and TCP port (starting at 4403) is opened. 
Before running this, build the Linux native application of Meshtastic-device which can be done on your Linux PC using PlatformIO. Select 'native' and click on 'build'. Locate the generated binary file, which will probably be in *Meshtastic-device/.pio/build/native*. Either copy the file called 'program' to the directory where you will be running the Python script from, or add the full path as argument after *--p*. For example: ```python3 interactiveSim.py 3 --p /home/User/Meshtastic-device/.pio/build/native```. 



https://user-images.githubusercontent.com/78759985/193409669-e8b6be37-6c73-40b3-84a4-8757ab4b7dfd.mp4

