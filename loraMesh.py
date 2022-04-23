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

	def onAir(self, packet):
		if not self.pipes:
			raise RuntimeError('There are no output pipes.')
		events = [store.put(packet) for store in self.pipes]
		return self.env.all_of(events)  # Condition event for all "events"


	def latency(self, packet):
		yield self.env.timeout(packet.recTime)
		if not self.pipes:
			raise RuntimeError('There are no output pipes.')
		events = [store.put(packet) for store in self.pipes]
		return self.env.all_of(events)  # Condition event for all "events"


	def put(self, packet):
		self.env.process(self.latency(packet))
		if not self.pipes:
			raise RuntimeError('There are no output pipes.')
		events = [store.put(packet) for store in self.pipes]
		return self.env.all_of(events)  # Condition event for all "events"
       

	def get_output_conn(self):
		pipe = simpy.Store(self.env, capacity=self.capacity)
		self.pipes.append(pipe)
		return pipe


getParams(sys.argv)	
env = simpy.Environment()
bc_pipe = BroadcastPipe(env)

# list of received packets
packets = []
packetsAtN = [[] for _ in range(conf.NR_NODES)]

graph = Graph()
for i in range(conf.NR_NODES):
	if len(conf.xs) == 0: 
		node = MeshNode(env, bc_pipe, i, 0.5*conf.SIMTIME, packetsAtN, packets)
	else: 
		node = MeshNode(env, bc_pipe, i, 0.5*conf.SIMTIME, packetsAtN, packets, conf.xs[i], conf.ys[i])
	graph.add(node)
	conf.nodes.append(node)
print("Nodes created")

# start simulation
env.run(until=conf.SIMTIME)

# compute data extraction rate
print("====== END OF SIMULATION ======")
print('Number of messages created:', conf.packetSeq)
sent = len(packets)
potentialReceivers = sent*(conf.NR_NODES-1)
print('Number of packets sent:', sent, 'to', potentialReceivers, 'potential receivers')
nrCollisions = sum([1 for p in packets for n in conf.nodes if p.collidedAtN[n.nodeid] == True])
print("Number of collisions:", nrCollisions)
nrSensed = sum([1 for p in packets for n in conf.nodes if p.sensedByN[n.nodeid] == True])
print("Number of packets sensed:", nrSensed)
nrReceived = sum([1 for p in packets for n in conf.nodes if p.receivedAtN[n.nodeid] == True])
print("Number of packets received:", nrReceived)
if nrSensed != 0:
	collisionRate = float((nrCollisions)/nrSensed)
	print("Collision rate:", collisionRate)
else:
	print("No packets sensed.")
deliveryRate = float(nrReceived/potentialReceivers)
print("Delivery rate:", deliveryRate)
nodeReach = sum([len(set([p.seq for p in packetsAtN[n.nodeid] if p.origTxNodeId != n.nodeid])) for n in conf.nodes])/(conf.packetSeq*(conf.NR_NODES-1))
print("Node reachability:", nodeReach)
if nrReceived != 0:
	usefulness = conf.usefulPackets/nrReceived  # nr of packets that delivered to a packet to a new receiver out of all packets sent
	print("Ratio of packets reaching new receiver:", usefulness)
else:
	print('No packets received.')
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