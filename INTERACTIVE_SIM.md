# Interactive Simulator

The Python script *interactiveSim.py* uses the [Linux native application of Meshtastic](https://meshtastic.org/docs/software/other/docker) in order to simulate multiple instances of the device software. They will communicate using TCP via this script as if they did using their LoRa chip. The simulator will forward a message from the sender to all nodes that can hear it, based on their simulated positions and the pathloss model used (see [the README](README.md)). Collisions of packets are not (yet) simulated.  

## Usage
Please `git clone` or download this repository, navigate to the Meshtasticator folder (optionally create a virtual environment) and install the necessary requirements using: 
```pip install -r requirements.txt```.
The Interactive Simulator should be run as follows: 

```python3 interactiveSim.py <nrNodes> [--p <full-path-to-program>]```,

where nrNodes is the number of instances you want to launch. Note that for each instance a terminal and TCP port (starting at 4403) is opened. If the number of nodes is given, they will be randomly placed, otherwise you first have to place the nodes on a plot.
Before running this, build the Linux native application of Meshtastic-device which can be done on your Linux PC using PlatformIO. Select 'native' and click on 'build'. Locate the generated binary file, which will probably be in *Meshtastic-device/.pio/build/native/*. Either copy the file called 'program' to the directory where you will be running the Python script from, or add the full path as argument after *--p*. For example: ```python3 interactiveSim.py 3 --p /home/User/Meshtastic-device/.pio/build/native/```.

https://user-images.githubusercontent.com/78759985/193409669-e8b6be37-6c73-40b3-84a4-8757ab4b7dfd.mp4

The nodes first exchange their NodeInfo. Afterwards, you can let them send messages. To modify this, check the section at the end of the script in the last 'try' clause. 
Once the nodes are done sending, you can close them by pressing Control+c or just wait for the timeout. Then you will see a plot where you can enter a message ID to plot its route. Hover over an arc to see some information and click to remove the information afterwards. Hovering is sometimes a bit laggy, so you might have to hover over it multiple times.

![](/img/route_plot.png)