from . import config as conf
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
import os
import pandas as pd
import time
import numpy as np


def loadData(fname):
	data = pd.read_csv(fname, header = 0)
	return data
	
	
def getParams(args):
	if len(args) < 2:
		print("Usage: ./loraMesh <modem> [nr_nodes] [--from-file <file_name>]")
		exit(1)
	else:
		if int(args[1]) > 6 or int(args[1]) < 0:
			print('Modem should be 0-6 for Short Fast to Very Long Slow')
			exit(1)
		conf.MODEM = int(args[1]) 
		if len(args) > 2:
			if type(args[2]) == str and ("--from-file" in args[2]):
				string = args[3]
				conf.xs = np.load("out/coords/"+string+"_x.npy")
				conf.ys = np.load("out/coords/"+string+"_y.npy")
				conf.NR_NODES = len(conf.xs)
			else:
				conf.NR_NODES = int(args[2])
		else: 
			[conf.xs, conf.ys] = genScenario()
			conf.NR_NODES = len(conf.xs)
		
	print("Number of nodes:", conf.NR_NODES)
	print("Simtime: ", conf.SIMTIME)
	print("Modem: ", conf.MODEM)
	print("Interference level:", conf.INTERFERENCE_LEVEL)
	
	if not os.path.isdir('out'):
		os.mkdir('out')
		os.mkdir('out/report')
		os.mkdir('out/graphics')


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
		np.save('out/coords/'+filename+'_x.npy', np.array(nodeX))
		np.save('out/coords/'+filename+'_y.npy', np.array(nodeY))
	
	return nodeX, nodeY


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
		self.fig, self.ax = plt.subplots()

		plt.suptitle('Placement of {} nodes\nin a range of {}m'.format(
				conf.NR_NODES, 
				conf.RAY))
		self.ax.set_xlim(-self.xmax, self.xmax)
		self.ax.set_ylim(-self.ymax, self.ymax)
		self.ax.set_xlabel('x (m)')
		self.ax.set_ylabel('y (m)')
		
		
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


