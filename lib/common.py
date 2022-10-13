from meshtastic import BROADCAST_NUM
from matplotlib import patches
from . import config as conf
from . import phy 
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use("TkAgg")
from matplotlib.widgets import Button, TextBox
import os
import simpy
import pandas as pd
import time
import numpy as np
import random
HW_ID_OFFSET = 16
TCP_PORT_OFFSET = 4403
	
def getParams(args):
	if len(args) > 3:
		print("Usage: ./loraMesh [nr_nodes] [--from-file <file_name>]")
		print("Do not specify the number of nodes when reading from a file.")
		exit(1)
	else:
		if len(args) > 1:
			if type(args[1]) == str and ("--from-file" in args[1]):
				string = args[2]
				conf.xs = np.load(os.path.join("out", "coords", string+"_x.npy"))
				conf.ys = np.load(os.path.join("out", "coords", string+"_y.npy"))
				conf.NR_NODES = len(conf.xs)
			else:
				conf.NR_NODES = int(args[1])
		else: 
			[conf.xs, conf.ys] = genScenario()
			conf.NR_NODES = len(conf.xs)
		
	print("Number of nodes:", conf.NR_NODES)
	print("Modem:", conf.MODEM)
	print("Simulation time (s):", conf.SIMTIME/1000)
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
	plt.xlim(-(conf.XSIZE/2+1)+conf.OX, conf.OX+conf.XSIZE/2+1)
	plt.ylim(-(conf.YSIZE/2+1)+conf.OY, conf.OY+conf.YSIZE/2+1)
	add_button_ax = fig.add_axes([0.5-0.05, 0.05, 0.2, 0.04])
	add_button = Button(add_button_ax, 'Continue')

	def plotting():
		ax.cla()
		ax.set_xlabel('x (m)')
		ax.set_ylabel('y (m)')
		ax.set_xlim(-(conf.XSIZE/2+1)+conf.OX, conf.OX+conf.XSIZE/2+1)
		ax.set_ylim(-(conf.YSIZE/2+1)+conf.OY, conf.OY+conf.YSIZE/2+1)
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
		if not os.path.isdir(os.path.join("out", "coords")):
			if not os.path.isdir("out"):
				os.mkdir("out")
			os.mkdir(os.path.join("out", "coords"))
		np.save(os.path.join("out", "coords", filename+"_x.npy"), np.array(nodeX))
		np.save(os.path.join("out", "coords", filename+"_y.npy"), np.array(nodeY))
	
	return nodeX, nodeY


def findRandomPosition(nodes):
	foundMin = True
	foundMax = False
	tries = 0
	while not (foundMin and foundMax):
		a = random.random()
		b = random.random()
		posx = a*conf.XSIZE+conf.OX-conf.XSIZE/2
		posy = b*conf.YSIZE+conf.OY-conf.YSIZE/2
		if len(nodes) > 0:
			for n in nodes:
				dist = calcDist(n.x, n.y, posx, posy)
				if dist < conf.MINDIST:
					foundMin = False
					break
				pathLoss = phy.estimatePathLoss(dist, conf.FREQ)
				rssi = conf.PTX + conf.GL - pathLoss
				if rssi >= conf.SENSMODEM[conf.MODEM]:
					foundMax = True
			if foundMin and foundMax:
				x = posx
				y = posy
		else:
			x = posx
			y = posy
			foundMin = True
			foundMax = True
		tries += 1
		if tries > 1000:
			print('Could not find a location to place the node. Try increasing XSIZE/YSIZE or decreasing MINDIST.')
			break
	return x,y


def calcDist(x0, y0, x1, y1): 
	return np.sqrt(((abs(x0-x1))**2)+((abs(y0-y1))**2))


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
	# do not plot time sequences with messages that were only generated but not sent 
	timeSequences = [t for t in timeSequences if max([m.endTime for m in t]) != 0]
	# plot each time sequence in new figure
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
		plt.ylabel('Node ID')
		plt.xlim(minTime-0.03*(maxTime-minTime), maxTime)
		plt.show(block=False)
		plt.waitforbuttonpress()
		plt.close()


def move_figure(fig, x, y):
  fig.canvas.manager.window.wm_geometry("+%d+%d" % (x, y))


def simReport(data, subdir, param):	
	fname = "simReport_{}_{}.csv".format(conf.MODEM, param)
	if not os.path.isdir(os.path.join("out", "report", subdir)):
		if not os.path.isdir("out"):
			os.mkdir("out")
		if not os.path.isdir(os.path.join("out", "report")):
			os.mkdir(os.path.join("out", "report"))
		os.mkdir(os.path.join("out", "report", subdir))
	df_new = pd.DataFrame(data)
	df_new.to_csv(os.path.join("out", "report", subdir, fname), index=False)		
		

class BroadcastPipe(object):
	def __init__(self, env, capacity=simpy.core.Infinity):
		self.env = env
		self.capacity = capacity
		self.pipes = []


	def latency(self, packet):
		# wait time that packet is on the air
		yield self.env.timeout(packet.timeOnAir)
		if not self.pipes:
			raise RuntimeError('There are no output pipes.')
		events = [store.put(packet) for store in self.pipes]
		return self.env.all_of(events) 


	def put(self, packet):
		self.env.process(self.latency(packet))
		# this mimics start of reception
		if not self.pipes:
			raise RuntimeError('There are no output pipes.')
		events = [store.put(packet) for store in self.pipes]
		return self.env.all_of(events)
       

	def get_output_conn(self):
		pipe = simpy.Store(self.env, capacity=self.capacity)
		self.pipes.append(pipe)
		return pipe


class Graph():
	def __init__(self):
		self.xmax = conf.XSIZE/2 +1
		self.ymax = conf.YSIZE/2 +1
		self.packets = []
		self.fig, self.ax = plt.subplots()
		plt.suptitle('Placement of {} nodes'.format(
				conf.NR_NODES))
		self.ax.set_xlim(-self.xmax+conf.OX, self.xmax+conf.OX)
		self.ax.set_ylim(-self.ymax+conf.OY, self.ymax+conf.OY)
		self.ax.set_xlabel('x (m)')
		self.ax.set_ylabel('y (m)')
		move_figure(self.fig, 200, 200)

		
	def addNode(self, node):
		# place the node
		if not conf.RANDOM:
			self.ax.annotate(str(node.nodeid), (node.x-5, node.y+5))
		self.ax.plot(node.x, node.y, marker="o", markersize = 2.5, color = "grey")
		self.fig.canvas.draw_idle()
		plt.pause(0.05)


	def initRoutes(self, defaultHopLimit):
		self.arrows = []
		self.txts = []
		self.annots = []
		self.firstTime = True
		self.defaultHopLimit = defaultHopLimit
		self.fig.subplots_adjust(bottom=0.2)
		axbox = self.fig.add_axes([0.5, 0.04, 0.1, 0.06])
		self.text_box = TextBox(axbox, "Message ID: ", initial="0")
		self.text_box.disconnect("button_press_event")
		self.text_box.on_submit(self.submit)
		self.fig.canvas.mpl_connect("motion_notify_event", self.hover)
		self.fig.canvas.mpl_connect("button_press_event", self.onClick)
		print("Enter a message ID on the plot to show its route.")
		self.fig.canvas.draw_idle()
		plt.show()


	def clearRoute(self):
		for arr in self.arrows.copy():
			arr.remove()
			self.arrows.remove(arr)
		for ann in self.annots.copy():
			ann.remove()
			self.annots.remove(ann)


	def plotRoute(self, messageId):
		if self.firstTime: 
			print('Hover over an arc to show some info and click to remove it afterwards.')
		self.firstTime = False
		packets = [p for p in self.packets if p.localId == messageId]
		if len(packets) > 0:
			self.clearRoute()
			style = "Simple, tail_width=0.5, head_width=4, head_length=8"
			for p in packets:
				tx = p.transmitter
				rxs = p.receivers
				for i,rx in enumerate(rxs):
					kw = dict(arrowstyle=style, color=plt.cm.Set1(tx.nodeid))
					patch = patches.FancyArrowPatch((tx.x, tx.y), (rx.x, rx.y), connectionstyle="arc3,rad=.1", **kw)
					self.ax.add_patch(patch)

					if int(p.packet["to"]) == BROADCAST_NUM:
						to = "All"
					else: 
						to = str(p.packet["to"]-HW_ID_OFFSET)

					if "hopLimit" in p.packet:
						hopLimit = p.packet["hopLimit"]
					else:
						hopLimit = None

					if hopLimit == self.defaultHopLimit:
						msgType = "Original\/message"
					elif p.packet["priority"] != "ACK":
						if int(p.packet['from'])-HW_ID_OFFSET == rx.nodeid:
							msgType = "Implicit\/ACK"
						else:
							if to == "All":
								msgType = "Rebroadcast"
							else:
								msgType = "Forwarding\/packet"
					elif p.packet["priority"] == "ACK":
						msgType = "ACK"
					else: 
						msgType = "Other"

					fields = []
					msgTypeField = r"$\bf{"+msgType+"}$"
					fields.append(msgTypeField)
					origSenderField = "Original sender: "+str(p.packet["from"]-HW_ID_OFFSET)
					fields.append(origSenderField)
					destField = "Destination: "+to
					fields.append(destField)
					portNumField = "Portnum: "+str(p.packet["decoded"]["simulator"]["portnum"])
					fields.append(portNumField)
					if hopLimit:
						hopLimitField = "HopLimit: "+str(hopLimit)
						fields.append(hopLimitField)
					rssiField = "RSSI: "+str(round(p.rssis[i], 2)) +" dBm"
					fields.append(rssiField)
					table = ""
					for i,f in enumerate(fields): 
						table += f
						if i != len(fields)-1:
							table += "\n"
					annot = self.ax.annotate(table, xy=((tx.x+rx.x)/2, rx.y+150), bbox=dict(boxstyle="round", fc="w"))
					annot.get_bbox_patch().set_facecolor(patch.get_facecolor())
					annot.get_bbox_patch().set_alpha(0.4)
					annot.set_visible(False)
					self.arrows.append(patch)
					self.annots.append(annot)
			self.fig.canvas.draw_idle() 
			self.fig.suptitle('Route of message '+str(messageId)+' and ACKs')
		else:
			print('Could not find message ID.')


	def hover(self, event):
		if event.inaxes == self.ax:
			for i,a in enumerate(self.arrows):
				annot = self.annots[i]
				cont, _ = a.contains(event)
				if cont:
						annot.set_visible(True)
						self.fig.canvas.draw()
						break


	def onClick(self, event):
		for annot in self.annots:
			if annot.get_visible():
				annot.set_visible(False)
				self.fig.canvas.draw_idle()


	def submit(self, val):
		messageId = int(val)
		self.plotRoute(messageId)


	def save(self):
		if not os.path.isdir(os.path.join("out", "graphics")):
			if not os.path.isdir("out"):
				os.mkdir("out")
			os.mkdir(os.path.join("out", "graphics"))
			
		plt.savefig(os.path.join("out", "graphics", "placement_"+str(conf.NR_NODES)))

