
from . import config as conf
from . import phy 
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.widgets import Button, Slider, CheckButtons, TextBox
import os
import numpy as np
import random
import yaml 
	

def getParams(args):
	if len(args) > 3:
		print("Usage: ./loraMesh [nr_nodes] [--from-file [file_name]]")
		print("Do not specify the number of nodes when reading from a file.")
		exit(1)
	else:
		if len(args) > 1:
			if type(args[1]) == str and ("--from-file" in args[1]):
				if len(args) > 2:
					string = args[2]
				else:
					string = 'nodeConfig.yaml'
				with open(os.path.join("out", string), 'r') as file: 
					config = yaml.load(file, Loader=yaml.FullLoader)
			else:
				conf.NR_NODES = int(args[1])
				config = [None for _ in range(conf.NR_NODES)]
		else: 
			config = genScenario()
		if config[0] is not None:
			conf.NR_NODES = len(config.keys())
		if conf.NR_NODES < 2:
			print("Need at least two nodes.")
			exit(1)
		
	print("Number of nodes:", conf.NR_NODES)
	print("Modem:", conf.MODEM)
	print("Simulation time (s):", conf.SIMTIME/1000)
	print("Period (s):", conf.PERIOD/1000)
	print("Interference level:", conf.INTERFERENCE_LEVEL)
	return config


def setBatch(simNr):
	conf.SEED = simNr
	conf.VERBOSE = False


def genScenario(plotRange = True):
	save = True  # set to True if you want to save the coordinates of the nodes 
	nodeX = []
	nodeY = []
	nodeZ = []
	nodeRouter = []
	nodeHopLimit = []
	nodeTxts = []
	gains = []

	fig = plt.figure()
	ax = fig.add_subplot(111)
	fig.subplots_adjust(bottom=0.20, right=0.85) # Make room for button and config
	title = "Double click to place a node. Then change its config (optional)."
	plt.title(title)
	plt.xlabel('x (m)')
	plt.ylabel('y (m)')
	plt.xlim(-(conf.XSIZE/2+1)+conf.OX, conf.OX+conf.XSIZE/2+1)
	plt.ylim(-(conf.YSIZE/2+1)+conf.OY, conf.OY+conf.YSIZE/2+1)
	# 'Start simulation' button
	button_ax = fig.add_axes([0.37, 0.05, 0.2, 0.06])
	button = Button(button_ax, 'Start simulation', color='red', hovercolor='green')
	# Router checkbox
	router_ax = fig.add_axes([0.86, 0.67, 0.12, 0.2])
	router_ax.set_axis_off()
	checkButton = CheckButtons(router_ax, ['Router'], [conf.router])
	router_ax.set_visible(False)
	# HopLimit slider
	slider_ax = fig.add_axes([0.86, 0.42, 0.1, 0.25])
	slider = Slider(slider_ax, 'HopLimit', 0, 7, conf.hopLimit, valstep=1, orientation="vertical")
	slider_ax.set_visible(False)
	# Height textbox
	height_ax = fig.add_axes([0.89, 0.30, 0.05, 0.04])
	height_textbox = TextBox(height_ax, 'Height (m)', conf.HM, textalignment='center')
	height_ax.set_visible(False)
	textBoxLabel = height_textbox.ax.get_children()[0]
	textBoxLabel.set_position([0.5, 1.75]) 
	textBoxLabel.set_verticalalignment('top')
	textBoxLabel.set_horizontalalignment('center')
	# Antenna gain textbox
	gain_ax = fig.add_axes([0.89, 0.19, 0.05, 0.04])
	gain_textbox = TextBox(gain_ax, 'Antenna \ngain (dBi)', conf.GL, textalignment='center')
	gain_ax.set_visible(False)
	gainLabel = gain_textbox.ax.get_children()[0]
	gainLabel.set_position([0.5, 2.5]) 
	gainLabel.set_verticalalignment('top')
	gainLabel.set_horizontalalignment('center')

	def plotting():
		ax.cla()
		ax.set_xlabel('x (m)')
		ax.set_ylabel('y (m)')
		ax.set_xlim(-(conf.XSIZE/2+1)+conf.OX, conf.OX+conf.XSIZE/2+1)
		ax.set_ylim(-(conf.YSIZE/2+1)+conf.OY, conf.OY+conf.YSIZE/2+1)
		ax.set_title(title)
		if plotRange:
			for i,(nx,ny) in enumerate(zip(nodeX, nodeY)):
				ax.annotate(str(i), (nx-5, ny+5))
				circle = plt.Circle((nx, ny), radius=phy.MAXRANGE, color=plt.cm.Set1(i), alpha=0.1)
				ax.add_patch(circle)
		if len(nodeTxts) > 0:
			# Remove last 'Configure node x' text
			nodeTxts[-1].set_visible(False)
		else:
			# After first node is placed, display config options
			router_ax.set_visible(True)
			slider_ax.set_visible(True)
			height_ax.set_visible(True)
			gain_ax.set_visible(True)
		nodeTxts.append(plt.text(0.92, 0.80, 'Configure \nnode '+str(len(nodeX)-1)+':', \
			fontweight='bold', horizontalalignment='center', transform=fig.transFigure))

		ax.scatter(nodeX, nodeY)
		fig.canvas.draw_idle()
		fig.canvas.get_tk_widget().focus_set()


	def submit(mouse_event):
		if (len(nodeX)) < 2:
			print("Need at least two nodes.")
			exit(1)
		# Save last config
		nodeZ.append(float(height_textbox.text))
		nodeRouter.append(checkButton.get_status()[0])
		nodeHopLimit.append(slider.val)
		gains.append(float(gain_textbox.text))
		fig.canvas.mpl_disconnect(cid)
		plt.close()

	button.on_clicked(submit)

	def onclick(event):
		if event.dblclick:
			if len(nodeX) > 0:
				# Save config of previous node
				nodeZ.append(float(height_textbox.text))
				isRouter = checkButton.get_status()[0]
				nodeRouter.append(isRouter)
				nodeHopLimit.append(slider.val)
				gains.append(float(gain_textbox.text))
				# Reset config values
				height_textbox.set_val(conf.HM)
				if isRouter:
					checkButton.set_active(0)
				slider.set_val(conf.hopLimit)
				gain_textbox.set_val(conf.GL)
			
			# New node placement
			nodeX.append(float(event.xdata))
			nodeY.append(float(event.ydata))
			plotting()

	cid = fig.canvas.mpl_connect('button_press_event', onclick)
	plt.show()
	# Save node configuration in a dictionary
	nodeDict = {n: {'x': nodeX[n], 'y': nodeY[n], 'z': nodeZ[n], \
		'isRouter': nodeRouter[n], 'hopLimit':nodeHopLimit[n], \
		'antennaGain': gains[n]} for n in range(len(nodeX))}
	if save:
		if not os.path.isdir("out"):
			os.mkdir("out")
		with open(os.path.join("out", "nodeConfig.yaml"), 'w') as file:
			yaml.dump(nodeDict, file) 
	
	return nodeDict


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
				dist = calcDist(n.x, posx, n.y, posy)
				if dist < conf.MINDIST:
					foundMin = False
					break
				pathLoss = phy.estimatePathLoss(dist, conf.FREQ)
				rssi = conf.PTX + 2*conf.GL - pathLoss
				# At least one node should be able to reach it
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


def calcDist(x0, x1, y0, y1, z0=0, z1=0): 
	return np.sqrt(((abs(x0-x1))**2)+((abs(y0-y1))**2)+((abs(z0-z1)**2)))


scheduleIdx = 0
def plotSchedule(packets, messages):
	def drawSchedule(i):
		t = timeSequences[i]
		plt.suptitle('Time schedule {}/{}\nDouble click to continue.'.format(i+1, len(timeSequences)))
		for p in packets:  # collisions
			if p.seq in [m.seq for m in t]: 
				for rxId, bool in enumerate(p.collidedAtN):
					if bool:
						plt.barh(rxId, p.timeOnAir, left=p.startTime, color='red', edgecolor='r')
		for p in packets:  # transmissions
			if p.seq in [m.seq for m in t]:  
				if p.isAck: 
					color = 'orange'
				else: 
					color = 'blue'
				plt.barh(p.txNodeId, p.timeOnAir, left=p.startTime, color=color, edgecolor='k')
				plt.text(p.startTime+p.timeOnAir/2, p.txNodeId, str(p.seq), horizontalalignment='center', verticalalignment='center', fontsize=12)
		for p in packets:  # receptions
			if p.seq in [m.seq for m in t]:  
				for rxId, bool in enumerate(p.receivedAtN):
					if bool:
						plt.barh(rxId, p.timeOnAir, left=p.startTime, color='green', edgecolor='green')
		maxTime = 0
		for m in t:  # message generations
			plt.arrow(m.genTime, m.origTxNodeId-0.4, 0, 0.5, head_width=0.02*(m.endTime-m.genTime), head_length=0.3, fc='k', ec='k')
			plt.text(m.genTime, m.origTxNodeId+0.51, str(m.seq), horizontalalignment='center', verticalalignment='center', fontsize=12)
		maxTime = max([m.endTime for m in t])
		minTime = min([m.genTime for m in t])
		
		plt.xlabel('Time (ms)')
		plt.ylabel('Node ID')
		plt.yticks([0]+list(range(conf.NR_NODES)), label=[str(n) for n in [0]+list(range(conf.NR_NODES))])
		plt.xlim(minTime-0.03*(maxTime-minTime), maxTime)
		plt.show()	

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

	# plot each time sequence
	fig = plt.figure()
	move_figure(fig, 900, 200)
	def onclick(event):
		if event.dblclick:
			global scheduleIdx
			plt.cla()
			scheduleIdx += 1
			if scheduleIdx < len(timeSequences):
				drawSchedule(scheduleIdx)	
			else:
				plt.close('all')

	fig.canvas.mpl_connect('button_press_event', onclick)
	drawSchedule(0)


def move_figure(fig, x, y):
  fig.canvas.manager.window.wm_geometry("+%d+%d" % (x, y))


class Graph():
	def __init__(self, plotRange=False):
		self.plotRange = plotRange
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
		if self.plotRange:
			circle = plt.Circle((node.x, node.y), radius=phy.MAXRANGE, color=plt.cm.Set1(node.nodeid), alpha=0.1)
			self.ax.add_patch(circle)
		self.fig.canvas.draw_idle()
		plt.pause(0.1)


	def save(self):
		if not os.path.isdir(os.path.join("out", "graphics")):
			if not os.path.isdir("out"):
				os.mkdir("out")
			os.mkdir(os.path.join("out", "graphics"))
			
		plt.savefig(os.path.join("out", "graphics", "placement_"+str(conf.NR_NODES)))

