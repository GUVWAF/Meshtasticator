# Interactive simulator

The Python script *interactiveSim.py* uses the [Linux native application of Meshtastic](https://meshtastic.org/docs/software/linux-native) in order to simulate multiple instances of the device software. They will communicate using TCP via this script as if they did using their LoRa chip. The simulator will forward a message from the sender to all nodes that can hear it, based on their simulated positions and the pathloss model used (see [Pathloss model](#Pathloss-model)). Collisions of packets are not (yet) simulated.  

## Usage
Please `git clone` or download this repository, navigate to the Meshtasticator folder (optionally create a virtual environment) and install the necessary requirements using: 
```pip install -r requirements.txt```. On a Mac, you might need python-tk as well (```brew install python-tk```). 

Build the Linux native application of Meshtastic-device (firmware), which can be done on your Linux PC using [PlatformIO](https://meshtastic.org/docs/development/firmware/build) or using [Docker](https://meshtastic.org/docs/software/linux-native#usage-with-docker). 
- Using PlatformIO, select 'native' and click on 'build'. Locate the generated binary file, which will probably be in *Meshtastic-device/.pio/build/native/*. Either copy the file called 'program' to the directory where you will be running the Python script from, or add the full path as argument after *--p*. For example: ```python3 interactiveSim.py 3 --p /home/User/Meshtastic-device/.pio/build/native/```.
- For usage with Docker, first build the container using ```docker build -t meshtastic-device .``` when in the *Meshtastic-device* (or *firmware*) directory. Install the Docker Python API with ```pip3 install docker```. Make sure the Docker daemon or Desktop application is running. Then run the interactive simulator with *--d* as argument, e.g.: ```python3 interactiveSim.py 3 --d```.

The interactive simulator can be run as follows: 

```python3 interactiveSim.py [nrNodes] [--p <full-path-to-program>]```,

where *nrNodes* (optional) is the number of instances you want to launch. Note that for each instance a terminal and TCP port (starting at 4403) is opened. If the number of nodes is given, they will be randomly placed, otherwise you first have to place the nodes on a plot.

The nodes first exchange their NodeInfo. Afterwards, you can let them send messages. To specifiy what you want to send, modify the script in the 'try' clause. 
Depending on the number of nodes, exchanging the NodeInfo might take quite some time. You can also disable these by removing setIntervalFromNow() in the NodeInfoModule (and PositionModule) in the device firmware. This works because the simulator already knows the NodeIDs. 
Once the nodes are done sending, you can close them by pressing Control+c or just wait for the timeout set at the end of the 'try' clause. Then you will see a plot where you can enter a message ID to plot its route. Hover over an arc to see some information and click to remove the information afterwards. Hovering is sometimes a bit laggy, so you might have to hover over it multiple times.

![](/img/route_plot2.png)

## Pathloss model
The simulator uses a pathloss model to calculate how well a signal will propagate. Note that this is only a rough estimation of the physical environment and will not be 100% accurate, as it depends on a lot of factors. The implemented pathloss models are:
* ```0``` set the log-distance model  
* ```1``` set the Okumura-Hata for small and medium-size cities model  
* ```2``` set the Okumura-Hata for metropolitan areas  
* ```3``` set the Okumura-Hata for suburban enviroments  
* ```4``` set the Okumura-Hata for rural areas  
* ```5``` set the 3GPP for suburban macro-cell  
* ```6``` set the 3GPP for metropolitan macro-cell  

You can change the pathloss model and the area to simulate in */lib/config.py*. 
Here you can also specify which antenna gain (default is 0dBi) and height (default is 1m) is used for the nodes. Currently the LoRa settings are kept to the default of Meshtastic.
