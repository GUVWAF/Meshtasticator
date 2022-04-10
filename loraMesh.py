import simpy
import sys
from lib.node import *
import lib.config as conf
from lib.common import *
from lib.collision import *
from lib.channel import * 


class BroadcastPipe(object):
	def __init__(self, env, capacity=simpy.core.Infinity):
		self.env = env
		self.capacity = capacity
		self.pipes = []


	def latency(self, packet):
		yield self.env.timeout(packet.recTime)
		if not self.pipes:
			raise RuntimeError('There are no output pipes.')
		events = [store.put(packet) for store in self.pipes]
		return self.env.all_of(events)  # Condition event for all "events"


	def put(self, packet):
		self.env.process(self.latency(packet))
       

	def get_output_conn(self):
		pipe = simpy.Store(self.env, capacity=self.capacity)
		self.pipes.append(pipe)
		return pipe



if len(sys.argv) >= 2:
	getParams(sys.argv)	
else:
	print("Usage: ./loraMesh <nodes>")
	exit()

env = simpy.Environment()
bc_pipe = BroadcastPipe(env)

# list of received packets
packets = []
packetsAtN = [[] for _ in range(conf.NR_NODES)]
packetSeq = 0

graph = Graph()

for i in range(conf.NR_NODES):
	if i == 0 or i == 1:
		node = MeshNode(env, bc_pipe, i, 10000, packetsAtN, packets, packetSeq)
	else:
		node = MeshNode(env, bc_pipe, i, 9999999, packetsAtN, packets, packetSeq)
	graph.add(node)
	conf.nodes.append(node)
		
print("Nodes created")

# start simulation
env.run(until=conf.SIMTIME)

# compute data extraction rate
sent = len(packets)
potentialReceivers = sent*(conf.NR_NODES-1)
print('Number of packets sent', sent, 'to', potentialReceivers, 'potential receivers')
nrCollisions = sum([1 for p in packets for n in conf.nodes if p.collidedAtN[n.nodeid] == True])
print("Number of collisions:", nrCollisions)
nrSensed = sum([1 for p in packets for n in conf.nodes if p.sensedByN[n.nodeid] == True])
print("Number of packets sensed:", nrSensed)
nrReceived = sum([1 for p in packets for n in conf.nodes if p.receivedAtN[n.nodeid] == True])
print("Number of packets received:", nrReceived)
collisionRate = float((nrCollisions)/nrSensed)
print("Collision rate: ", collisionRate)
deliveryRate = float(nrReceived/potentialReceivers)
print("Delivery rate: ", deliveryRate)
graph.save()
if conf.RANDOM:
	data = {
		"Nodes": conf.NR_NODES,
		"PathLoss": conf.MODEL,
		"Modem": conf.MODEM, 
		"PktSent": sent,
		"CollisionRate": collisionRate,
		"DeliveryRate": deliveryRate,
	}
	finalReport(data)