from . import config as conf
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
import os
import simpy
import pandas as pd
import time
import numpy as np
	
	
def getParams(args):
	if len(args) > 3:
		print("Usage: ./loraMesh [nr_nodes] [--from-file <file_name>]")
		print("Do not specify the number of nodes when reading from a file.")
		exit(1)
	else:
		if len(args) > 1:
			if type(args[1]) == str and ("--from-file" in args[1]):
				string = args[2]
				conf.xs = np.load("out/coords/"+string+"_x.npy")
				conf.ys = np.load("out/coords/"+string+"_y.npy")
				conf.NR_NODES = len(conf.xs)
			else:
				conf.NR_NODES = int(args[1])
		else: 
			[conf.xs, conf.ys] = genScenario()
			conf.NR_NODES = len(conf.xs)
		
	print("Number of nodes:", conf.NR_NODES)
	print("Modem: ", conf.MODEM)
	print("Simulation time (s): ", conf.SIMTIME/1000)
	print("Period (s):", conf.PERIOD/1000)
	print("Interference level:", conf.INTERFERENCE_LEVEL)


def setBatch(simNr):
	conf.SEED = simNr
	conf.VERBOSE = False


def genScenario():
	save = True  # set to True if you want to save the coordinates of the nodes 
	filename = "coords"
	nodeX = []
	nodeY = []

	fig = plt.figure()
	ax = fig.add_subplot(111)
	fig.subplots_adjust(bottom=0.20)
	plt.title("Double click to place nodes. Press continue to start the simulation.")
	plt.xlabel('x (m)')
	plt.ylabel('y (m)')
	plt.xlim(-(conf.OX+conf.RAY+1), conf.OX+conf.RAY+1)
	plt.ylim(-(conf.OY+conf.RAY+1), conf.OY+conf.RAY+1)
	add_button_ax = fig.add_axes([0.5-0.05, 0.05, 0.2, 0.04])
	add_button = Button(add_button_ax, 'Continue')

	def plotting():
		ax.cla()
		ax.set_xlabel('x (m)')
		ax.set_ylabel('y (m)')
		ax.set_xlim(-(conf.OX+conf.RAY+1), conf.OX+conf.RAY+1)
		ax.set_ylim(-(conf.OY+conf.RAY+1), conf.OY+conf.RAY+1)
		ax.set_title("Double click to place nodes. Press continue to start the simulation.")
		ax.scatter(nodeX, nodeY)
		fig.canvas.draw_idle()


	def submit(mouse_event):
		fig.canvas.mpl_disconnect(cid)
		plt.close()

	add_button.on_clicked(submit)

	def onclick(event):
		if event.dblclick:
			x = float(event.xdata)
			y = float(event.ydata)
			nodeX.append(x)
			nodeY.append(y)
			plotting()

	cid = fig.canvas.mpl_connect('button_press_event', onclick)
	plt.show()
	if save:
		if not os.path.isdir('out/coords'):
			os.mkdir('out/coords')
		np.save('out/coords/'+filename+'_x.npy', np.array(nodeX))
		np.save('out/coords/'+filename+'_y.npy', np.array(nodeY))
	
	return nodeX, nodeY


def plotSchedule(packets, messages):
	maxTime = 0
	# combine all messages with overlapping packets in one time sequence 
	overlapping = [[m] for m in messages]
	for m in messages:
		m.endTime = max([p.endTime for p in packets if p.seq == m.seq])
	for m1 in messages:
		for m2 in messages:
			if m1 != m2:
				if m2.genTime <= m1.endTime and m2.endTime > m1.genTime:
					overlapping[m1.seq-1].append(m2)
	timeSequences = []
	multiples = [[] for _ in overlapping]
	for ind, o1 in enumerate(overlapping):
		for o2 in overlapping: 
			if set(o1).issubset(set(o2)):
				multiples[ind].append(set(o2))
		maxSet = max(multiples[ind], key=len)
		if maxSet not in timeSequences:
			timeSequences.append(maxSet)
	# print each time sequence in new figure
	for i,t in enumerate(timeSequences):
		fig = plt.figure()
		move_figure(fig, 900, 200)
		plt.suptitle('Time schedule {}/{}\nClick to continue.'.format(i+1, len(timeSequences)))
		for p in packets:  # collisions
			if p.seq in [m.seq for m in t]: 
				for rxId, bool in enumerate(p.collidedAtN):
					if bool:
						plt.barh(rxId, p.timeOnAir, left=p.startTime, color='red', edgecolor='r')
		for p in packets:  # transmissions
			if p.seq in [m.seq for m in t]:  
				plt.barh(p.txNodeId, p.timeOnAir, left=p.startTime, color='blue', edgecolor='k')
				plt.text(p.startTime+p.timeOnAir/2, p.txNodeId, str(p.seq), horizontalalignment='center', verticalalignment='center', fontsize=12)
		for p in packets:  # receptions
			if p.seq in [m.seq for m in t]:  
				for rxId, bool in enumerate(p.receivedAtN):
					if bool:
						plt.barh(rxId, p.timeOnAir, left=p.startTime, color='green', edgecolor='green')
		for m in t:  # message generations
			plt.arrow(m.genTime, m.origTxNodeId-0.4, 0, 0.5, head_width=0.02*(m.endTime-m.genTime), head_length=0.3, fc='k', ec='k')
			plt.text(m.genTime, m.origTxNodeId+0.51, str(m.seq), horizontalalignment='center', verticalalignment='center', fontsize=12)
		maxTime = max([m.endTime for m in t])
		minTime = min([m.genTime for m in t])
		
		plt.yticks([0]+list(range(conf.NR_NODES)), label=[str(n) for n in [0]+list(range(conf.NR_NODES))])
		plt.xlabel('Time (ms)')
		plt.ylabel('Transmitter ID')
		plt.xlim(minTime-0.03*(maxTime-minTime), maxTime)
		plt.show(block=False)
		plt.waitforbuttonpress()
		plt.close()


def move_figure(f, x, y):
  backend = matplotlib.get_backend()
  if backend == 'TkAgg':
    f.canvas.manager.window.wm_geometry("+%d+%d" % (x, y))
  elif backend == 'WXAgg':
    f.canvas.manager.window.SetPosition((x, y))
  else:
    f.canvas.manager.window.move(x, y)


def simReport(data, subdir, param):	
	fname = subdir+"simReport_{}_{}.csv".format(conf.MODEM, param)
	if not os.path.isdir('out/report/'+subdir):
		os.mkdir('out/report/'+subdir)
	df_new = pd.DataFrame(data)
	df_new.to_csv('out/report/{}'.format(fname), index=False)		
		

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
		yield self.env.timeout(packet.timeOnAir)
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


class Graph():
	def __init__(self):
		
		self.xmax = conf.OX + conf.RAY +1
		self.ymax = conf.OY + conf.RAY +1
		self.fig, self.ax = plt.subplots()

		plt.suptitle('Placement of {} nodes'.format(
				conf.NR_NODES))
		self.ax.set_xlim(-self.xmax, self.xmax)
		self.ax.set_ylim(-self.ymax, self.ymax)
		self.ax.set_xlabel('x (m)')
		self.ax.set_ylabel('y (m)')
		move_figure(self.fig, 200, 200)
		
		
	def add(self, node):
		# place the node
		if not conf.RANDOM:
			self.ax.annotate(str(node.nodeid), (node.x, node.y))
		self.ax.plot(node.x, node.y, marker="o", markersize = 2.5, color = "grey")
		self.fig.canvas.flush_events()
		time.sleep(.0001)


	def save(self):
		if not os.path.isdir('out/graphics'):
			os.mkdir('out/graphics')
			
		if conf.RANDOM:
			plt.savefig('out/graphics/placement_'+str(conf.NR_NODES))
		else:
			plt.savefig('out/graphics/placement')

