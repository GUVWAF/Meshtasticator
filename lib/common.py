from . import config as conf
import matplotlib.pyplot as plt
import os
import pandas as pd
import time
import numpy as np


def loadData(fname):
	data = pd.read_csv(fname, header = 0)
	return data
	
	
def getParams(args):
	if len(args) < 3:
		print("Usage: ./loraMesh <nr_nodes> <modem>")
		exit(1)
	else:
		conf.NR_NODES = int(args[1])
		conf.MODEM = int(args[2]) 
	print("Number of nodes:", conf.NR_NODES)
	print("Simtime: ", conf.SIMTIME)
	print("Modem: ", conf.MODEM)
	print("Interference level:", conf.INTERFERENCE_LEVEL)
	
	if not os.path.isdir('out'):
		os.mkdir('out')
		os.mkdir('out/report')
		os.mkdir('out/graphics')


def finalReport(data):	
	if not conf.FULL_COLLISION:
		title = "simple"
	else:
		title = ""
	
	fname = "finalReport_{}.csv".format(title)
	
	if not os.path.isfile('out/report/{}'.format(fname)):
		df_new = pd.DataFrame(data, index = [0])
		df_new.to_csv('out/report/{}'.format(fname), index=False)
	else:
		df = pd.read_csv('out/report/{}'.format(fname))
		df_new = pd.DataFrame(data, index=[df.ndim-1])
		df = pd.concat((df, df_new), ignore_index = True)
		df.to_csv('out/report/{}'.format(fname),index=False)		


def nodeReport(data):
	if not conf.FULL_COLLISION:
			title = "simple"
	else:
		title = ""

	fname = "nodesReport_mod{}_exp{}_{}.csv".format(conf.MODEL, conf.EXP, title)
	
	if not os.path.isfile('out/report/{}'.format(fname)):
		df_new = pd.DataFrame(data, index = [0])
		df_new.to_csv('out/report/{}'.format(fname), index=False)
	else:
		df = pd.read_csv('out/report/{}'.format(fname))
		df_new = pd.DataFrame(data, index=[df.ndim-1])
		df = pd.concat((df, df_new), ignore_index = True)
		df.to_csv('out/report/{}'.format(fname), index = False)	
		

class Graph():
	def __init__(self):
		
		self.xmax = conf.OX + conf.RAY +1
		self.ymax = conf.OY + conf.RAY +1
		plt.ion()
		
		self.fig, self.ax = plt.subplots()
		if conf.RANDOM:
			plt.suptitle('Placement of {} nodes\nin a range of {}m'.format(
				conf.NR_NODES, 
				conf.RAY
			))
		else:
			plt.suptitle('Placement of nodes\nin a range of {}m'.format(
				conf.RAY
			))
		self.ax.set_xlim(-self.xmax, self.xmax)
		self.ax.set_ylim(-self.ymax, self.ymax)
		self.ax.set_axis_off()
		
		# plot the contour
		x = np.linspace(-conf.RAY, conf.RAY, 100)
		y = np.linspace(-conf.RAY, conf.RAY, 100)
		x, y = np.meshgrid(x,y)
		circ = x**2 + y**2 - conf.RAY**2
		self.ax.contour(x,y,circ,[0] ,colors='k', linestyles = "dashed", linewidths = 1)
		
		self.fig.canvas.flush_events()
		time.sleep(.0001)
		
		
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
		plt.close


