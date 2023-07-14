#~ Version 1.1.0
#~ Author: T. Mullock (tjm66@cam.ac.uk)
#~ Python version 3.7

import cv2
import tkinter as tk
from tkinter import font
from tkinter import ttk
from tkinter import messagebox
import DoublePendulum_PivotMass as simulation
import DoublePendulumProgram as pend
import time
from threading import Thread
import webbrowser
import threading
import queue
import csv
import os
try:
	import picamera	#if running on computer that is not connected to the camera, can still run off a pre-recorded video
except Exception as e:
	print(e)
from PIL import Image

import numpy as np

#emailing stuff
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate
from email import encoders

import matplotlib
import matplotlib.figure
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

#create globals to store all the lab's data in to be exported at the end... actually not used in this version of the program
global a_global, b_global, t_global, name_global
a_global, b_global, t_global, name_global = [], [], [], []

global crsids
crsids = []

def modeshapes_link():
	webbrowser.open(
		"https://nbviewer.jupyter.org/github/" +
		"CambridgeEngineering/PartIB-Paper1-Pendulum-Lab/" +
		"blob/master/src/Double_Pendulum_Small_Angle_Analysis.ipynb"
	)

class graph_area(tk.Frame):
	def __init__(self, master):
		tk.Frame.__init__(self, master)

		self.w_in = root.winfo_screenwidth()/100			#set the graph dimensions to take up the screen width and half the screen height
		self.h_in = root.winfo_screenheight()/100			#h_in and w_in are in inches. The conversion factor assumes 100dpi
		#~ self.h_step_in = master.step.winfo_height()		#this is height of the 'step' frame ... will these work on high def screens???
		self.fig = matplotlib.figure.Figure(figsize=(self.w_in, self.h_in*0.5))

		self.ax1 = self.fig.add_subplot(2,1,1)
		self.ax2 = self.fig.add_subplot(2,1,2)
		self.ax1.set_ylim([-180,180])						#set y limits
		self.ax2.set_ylim([-180,180])
		self.ax1.set_xlim(left=0, auto=True)
		self.ax1.yaxis.set_ticks(np.arange(-180, 181, 90))	#format x axis labels.
		self.ax2.yaxis.set_ticks(np.arange(-180, 181, 90))
		self.ax1.grid(linestyle='--', which='both')			#format gridlines
		self.ax2.grid(linestyle='--', which='both')
		self.ax1.set_ylabel('\u03b1 [\u00b0]')				#axis labels: 03b1 is alpha, 03b2 is beta, 00b0 is degree
		self.ax2.set_ylabel('\u03b2 [\u00b0]')
		self.ax2.set_xlabel('Time [s]')

		self.ax1.grid(True)									#remove the numbers from the x axis of the top plot for neatness
		self.ax1.xaxis.set_ticklabels([])

		self.fig.tight_layout()

		# Shrink current axis by 20% to make room for legend on the right hand side
		self.box = self.ax1.get_position()
		self.ax1.set_position([self.box.x0, self.box.y0, self.box.width * 0.85, self.box.height])
		self.box = self.ax2.get_position()
		self.ax2.set_position([self.box.x0, self.box.y0, self.box.width * 0.85, self.box.height])

		self.plot_graph(self.fig, redraw_canvas=True)

		self.first_time = True	#use this variable in function plot_graph

	def update_graph(self, fig, plot_number='', t=None, a=None, b=None, legend_a=' ', legend_b=' '):
		'''adds a line and an optional legend entry to each subplot'''
		#SOMETHING A BIT LIKE THIS
		if a is not None and b is not None and t is not None:	#only plot if there is data to plot
			self.ln1, = self.ax1.plot(t, a, label=legend_a)
			self.ln2, = self.ax2.plot(t, b, label=legend_b)

		self.ax1.set_xlim(left=-0.5, auto=True)					#rescale the axes
		self.ax2.set_xlim(left=-0.5, auto=True)
		self.fig.tight_layout()									#reposition the plot

		# Shrink current axis by 20% to make room for legend on the right hand side
		self.box = self.ax1.get_position()
		self.ax1.set_position([self.box.x0, self.box.y0, self.box.width * 0.85, self.box.height])
		self.box = self.ax2.get_position()
		self.ax2.set_position([self.box.x0, self.box.y0, self.box.width * 0.85, self.box.height])

		# Put a legend to the right of the current axis
		self.ax1.legend(loc='center left', bbox_to_anchor=(1, 0.5))
		#self.ax2.legend(loc='center left', bbox_to_anchor=(1, 0.5))

	def plot_graph(self, fig, redraw_canvas=False):
		if redraw_canvas:
			for widget in self.winfo_children():
				widget.destroy()					#find the id's of anything drawn on the canvas, and remove them
			self.canvas = FigureCanvasTkAgg(fig, master=self)
			self.canvas.get_tk_widget().pack(side='top', fill='both', expand=True)

			toolbar = NavigationToolbar2Tk(self.canvas, self)
			toolbar.update()
			self.canvas._tkcanvas.pack(side='top', fill='both', expand=1)

		self.canvas.draw()

class simulation_settings_window(tk.Toplevel):
	def __init__(self, master):
		tk.Toplevel.__init__(self, master)

		padding = {'padx':3, 'pady':3}
		self.default_font = tk.font.nametofont("TkDefaultFont")

		self.dt_label = tk.ttk.Label(self, text='Timestep of simulation [s]')
		self.dt_entry = tk.ttk.Entry(self, width=6, font=self.default_font)

		self.a_label = tk.ttk.Label(self, text='Length of arm a [m]')
		self.a_entry = tk.ttk.Entry(self, width=6, font=self.default_font)

		self.b_label = tk.ttk.Label(self, text='Length of arm b [m]')
		self.b_entry = tk.ttk.Entry(self, width=6, font=self.default_font)

		self.ma_label = tk.ttk.Label(self, text='Mass of arm a [kg]')
		self.ma_entry = tk.ttk.Entry(self, width=6, font=self.default_font)

		self.mb_label = tk.ttk.Label(self, text='Mass of arm b [kg]')
		self.mb_entry = tk.ttk.Entry(self, width=6, font=self.default_font)

		self.mp_label = tk.ttk.Label(self, text='Mass of the pivot [kg]')
		self.mp_entry = tk.ttk.Entry(self, width=6, font=self.default_font)


		self.reset_button = tk.ttk.Button(self, text='Reset', command=lambda:self.reset_simulation_settings())
		self.update_button = tk.ttk.Button(self, text='Update', command=lambda:self.update_simulation_settings())


		self.dt_label.grid	(row=0, column=0, sticky='E', **padding)
		self.dt_entry.grid	(row=0, column=1, sticky='W', **padding)

		self.a_label.grid			(row=1, column=0, sticky='E', **padding)
		self.a_entry.grid			(row=1, column=1, sticky='W', **padding)

		self.b_label.grid			(row=2, column=0, sticky='E', **padding)
		self.b_entry.grid			(row=2, column=1, sticky='W', **padding)

		self.ma_label.grid			(row=3, column=0, sticky='E', **padding)
		self.ma_entry.grid			(row=3, column=1, sticky='W', **padding)

		self.mb_label.grid			(row=4, column=0, sticky='E', **padding)
		self.mb_entry.grid			(row=4, column=1, sticky='W', **padding)

		self.mp_label.grid			(row=5, column=0, sticky='E', **padding)
		self.mp_entry.grid			(row=5, column=1, sticky='W', **padding)

		self.reset_button.grid		(row=6, column=0, sticky='E', **padding)
		self.update_button.grid		(row=6, column=1, sticky='W', **padding)

		self.dt_entry.insert(0, str(master.dt))
		self.a_entry.insert(0, str(master.a))
		self.b_entry.insert(0, str(master.b))
		self.ma_entry.insert(0, str(master.ma))
		self.mb_entry.insert(0, str(master.mb))
		self.mp_entry.insert(0, str(master.mp))

	def update_simulation_settings(self):
		master = self.master
		master.a = float(self.a_entry.get())
		master.b = float(self.b_entry.get())
		master.ma = float(self.ma_entry.get())
		master.mb = float(self.mb_entry.get())
		master.mp = float(self.mp_entry.get())
		master.dt = float(self.dt_entry.get())

	def reset_simulation_settings(self):
		master = self.master
		master.a = master.a_const
		master.b = master.b_const
		master.ma = master.ma_const
		master.mb = master.mb_const
		master.mp = master.mp_const
		master.dt = master.dt_const

		self.dt_entry.delete(0, 'end')
		self.a_entry.delete(0, 'end')
		self.b_entry.delete(0, 'end')
		self.ma_entry.delete(0, 'end')
		self.mb_entry.delete(0, 'end')
		self.mp_entry.delete(0, 'end')
		self.dt_entry.insert(0, str(master.dt))
		self.a_entry.insert(0, str(master.a))
		self.b_entry.insert(0, str(master.b))
		self.ma_entry.insert(0, str(master.ma))
		self.mb_entry.insert(0, str(master.mb))
		self.mp_entry.insert(0, str(master.mp))

class simulation_options(tk.Frame):
	def __init__(self, master):
		tk.Frame.__init__(self, master)

class ToggledFrame(tk.Frame):
	def __init__(self, master, text="", *args, **options):
		tk.Frame.__init__(self, master, *args, **options)

		self.text = text

		self.show = tk.IntVar()
		self.show.set(0)

		self.title_frame = tk.Frame(self)#, relief='sunken', borderwidth=1, bg='red')
		self.title_frame.pack(fill="x", expand=1)

		#~ tk.ttk.Label(self.title_frame, text=text).pack(side="left", fill="x", expand=1)

		self.toggle_button = tk.Checkbutton(
			self.title_frame, indicatoron=0, pady=0, offrelief='raised', bd=1, selectcolor='#EBEBEB',
			relief='flat', text='\u25bc    '+text, command=self.toggle,
			variable=self.show, anchor='w')

		self.toggle_button.pack(fill='x', expand=1)

		self.sub_frame = tk.Frame(self, relief="flat", borderwidth=1)

	def toggle(self):
		if bool(self.show.get()):
			self.sub_frame.pack(fill="x", expand=1)
			self.toggle_button.configure(text='\u25b2    '+self.text)
			self.update_idletasks()
		else:
			self.sub_frame.forget()
			self.toggle_button.configure(text='\u25bc    '+self.text)


class simulation_window(tk.Toplevel):
	def __init__(self, master):
		tk.Toplevel.__init__(self, master)

		master.simulation_window_open = 1
		self.protocol("WM_DELETE_WINDOW", self.on_closing_simulation_window)

		self.a = 0.185
		self.b = 0.172
		self.ma = 0.044
		self.mb = 0.019
		self.mp = 0.022
		self.dt = 0.02
		#settings above are varied by the settings popup, but settings below stay the same
		self.a_const = 0.185
		self.b_const = 0.172
		self.ma_const = 0.044
		self.mb_const = 0.019
		self.mp_const = 0.022
		self.dt_const = 0.02

		self.info_icon=tk.PhotoImage(file="info_icon.png")
		self.simulation_info_button = tk.ttk.Button(self, image=self.info_icon, command=lambda:self.show_simulation_message())
		image=self.info_icon

		self.alpha_entry = tk.ttk.Entry(self, width=4, font=master.master.default_font, validate='key', validatecommand=master.vcmd)
		self.alpha_label = tk.ttk.Label(self, text='\u03b1 [\u00b0]:')
		self.beta_entry = tk.ttk.Entry(self, width=4, font=master.master.default_font, validate='key', validatecommand=master.vcmd)
		self.beta_label = tk.ttk.Label(self, text='\u03b2 [\u00b0]:')

		self.more_toggle = ToggledFrame(self, text='More Options...', highlightbackground="#ACACAC", highlightcolor="#ACACAC", highlightthickness=1,)#borderwidth=1, bg='#505050')#relief='solid',

		self.settings_button = tk.ttk.Button(self.more_toggle.sub_frame, text='Simulation Parameters...', command=lambda:self.show_simulation_settings())

		self.options_info_button = tk.ttk.Button(self.more_toggle.sub_frame, image=self.info_icon, command=lambda:self.show_options_info())

		self.view_anim = tk.IntVar()
		self.view_anim.set(1)
		self.view_anim_checkbutton = tk.Checkbutton(self.more_toggle.sub_frame, text='View animation', variable=self.view_anim)

		self.adot_entry = tk.ttk.Entry(self.more_toggle.sub_frame, width=4, font=master.master.default_font, validate='key', validatecommand=master.vcmd)
		self.adot_label = tk.ttk.Label(self.more_toggle.sub_frame, text='d\u03b1/dt [\u00b0/s]:')
		self.bdot_entry = tk.ttk.Entry(self.more_toggle.sub_frame, width=4, font=master.master.default_font, validate='key', validatecommand=master.vcmd)
		self.bdot_label = tk.ttk.Label(self.more_toggle.sub_frame, text='d\u03b2/dt [\u00b0/s]:')

		self.small_angle_label = tk.ttk.Label(self.more_toggle.sub_frame, text='Small angle vibrations:')

		self.mode1_button = tk.ttk.Button(self.more_toggle.sub_frame, text='Mode 1', command=lambda:self.mode1())
		self.mode2_button = tk.ttk.Button(self.more_toggle.sub_frame, text='Mode 2', command=lambda:self.mode2())

		self.calculate_modes_button = tk.ttk.Button(self.more_toggle.sub_frame, text='Calculate mode shapes...', command=lambda:modeshapes_link())

		self.duration_entry = tk.ttk.Entry(self, width=4, font=master.master.default_font, validate='key', validatecommand=master.vcmd)
		self.duration_label = tk.ttk.Label(self, text='Duration [s]:')
		self.duration_entry.insert(0, "6")

		self.simulate_button = tk.ttk.Button(self, text='Simulate', command=lambda:self.simulate())

		#layout
		padding = master.padding

		self.alpha_label.grid				(row=3, column=0, sticky='E', **padding)
		self.alpha_entry.grid				(row=3, column=1, columnspan=5, sticky='WE', **padding)
		self.beta_label.grid				(row=4, column=0, sticky='E', **padding)
		self.beta_entry.grid				(row=4, column=1, columnspan=5, sticky='WE', **padding)
		self.duration_label.grid			(row=5, column=0, sticky='E', **padding)
		self.duration_entry.grid			(row=5, column=1, columnspan=5, sticky='WE', **padding)
		self.simulate_button.grid			(row=6, column=0, columnspan=5, **padding)
		self.simulation_info_button.grid	(row=6, column=5, **padding)

		self.more_toggle.grid				(row=7, column=0, columnspan=6, sticky='WE', **padding)

		self.settings_button.grid			(row=0, column=0, columnspan=2, sticky='W', **padding)
		self.options_info_button.grid		(row=0, column=2, **padding)
		self.view_anim_checkbutton.grid		(row=1, column=0, columnspan=3, sticky='W', **padding)

		self.adot_label.grid				(row=2, column=0, sticky='E', **padding)
		self.adot_entry.grid				(row=2, column=1, columnspan=2, sticky='WE', **padding)
		self.bdot_label.grid				(row=3, column=0, sticky='E', **padding)
		self.bdot_entry.grid				(row=3, column=1, columnspan=2, sticky='WE', **padding)

		self.small_angle_label.grid			(row=4, column=0, columnspan=3, sticky='W', **padding)

		self.mode1_button.grid				(row=5, column=0, sticky='E', **padding)
		self.mode2_button.grid				(row=5, column=1, columnspan=2, sticky='W', **padding)

		self.calculate_modes_button.grid	(row=6, column=0, columnspan=3, sticky='WE', **padding)

		self.alpha_entry.insert(0, "90")
		self.beta_entry.insert(0, "0")
		self.adot_entry.insert(0, "0")
		self.bdot_entry.insert(0, "0")

	def on_closing_simulation_window(self):
		self.master.simulation_window_open = 0
		self.destroy()

	def simulate(self, alpha_init=90, beta_init=0, adot_init=0, bdot_init=0, duration=6):
		master = self.master
		master.plot_number += 1
		plot_number = master.plot_number
		print('plot number {}'.format(plot_number))
		view_animation=self.view_anim.get()
		#master.info_text.set('Simulation in progress')
		if self.alpha_entry.get() != ''   : alpha_init = float(self.alpha_entry.get())		#set alpha, beta and duration to those entered,
		if self.beta_entry.get() != ''    : beta_init = float(self.beta_entry.get())		#unless there is nothing entred in the box.
		if self.adot_entry.get() != ''    : adot_init = float(self.adot_entry.get())			#in that case, simulation.run will use its default values
		if self.bdot_entry.get() != ''    : bdot_init = float(self.bdot_entry.get())
		if self.duration_entry.get() != '': duration = int(self.duration_entry.get())
		#run simulation
		time_, alpha, beta, modeshape, resonance = simulation.run(alpha=alpha_init, beta=beta_init, adot=adot_init, bdot=bdot_init,
																a=self.a, b=self.b, ma=self.ma, mb=self.mb, mp=self.mp, dt=self.dt,
																anim=view_animation, graph=False,
																length=duration, view_fourier=master.small_angle_table_1.view_fourier.get())
		time_, alpha, beta = pend.find_start_points(time_, alpha, beta)

		master.store_data(time_, alpha, beta, 'Simulation'+str(plot_number))
		master.write_to_csv(time_, alpha, beta, modeshape, resonance, plot_number, exp_type='Simulation')

		g = master.master.graph_area 	#locate the instance of graph area that was initially created.
		g.update_graph(g.fig, plot_number=plot_number, t=time_, a=alpha, b=beta, legend_a='Simulation'+str(plot_number), legend_b=' ')
		g.plot_graph(g.fig)
		#master.info_text.set('Simulation complete')

		if modeshape is not None and resonance is not None:
			master.small_angle_table_1.innards.show_modeshape_text(modeshape, resonance)

		self.lift()#make sure simulation window does not dissapear after graph plotted.

	def show_simulation_message(self):
		root_simulation_info = tk.Toplevel()
		root_simulation_info.title('Simulation info')

		self.simulation_message = tk.Message(root_simulation_info, width=400, text=('\
The simulation can be started by pressing the "Simulate" button. The initial conditions for \u03b1 and \u03b2 \
can be altered in the relevant boxes, and the length of the simulation in seconds can be varied in the "Duration" box.\
'))
		self.simulation_message.pack(padx=5, pady=5)

	def show_options_info(self):
		options_info_window = tk.Toplevel()
		options_info_window.title('Simulation options')
		self.options_info_message = tk.Message(options_info_window, width=400, text=(
'Parameters such as the mass of the pendulum in the simulation can be changed by pressing "Simulation Parameters" \n\n\
The "View animation" checkbox selects whether an animation of the pendulum is seen when the simulation is in progress.\n\n\
The initial speed of the arms in the simulation can be set using the relevant boxes (both default to zero, i.e. released from rest)\n\n\
Buttons labelled "Mode 1" and "Mode 2" automatically populate the initial conditions boxes with values to produce \
a single mode of vibration.\n\n\
Pressing the "Calculate mode shapes..." button follows a link to an azure notebook which shows the calculations required to produce the \
model for the simulation and how to calculate the mode shapes for small vibrations.'))
		self.options_info_message.pack(padx=5, pady=5)


	def show_simulation_settings(self):
		self.settings_window = simulation_settings_window(self)

	def mode1(self):
		v = simulation.find_mode(a=self.a, b=self.b, ma=self.ma, mb=self.mb, mp=self.mp)
		aonb_1 = v[0][0] / v[1][0]
		print(v)

		a = 5
		b = a/aonb_1

		self.alpha_entry.delete(0, 'end')
		self.beta_entry.delete(0, 'end')
		self.alpha_entry.insert(0, str(a))
		self.beta_entry.insert(0, str(b))

		print(self.alpha_entry.get())

	def mode2(self):
		v = simulation.find_mode(a=self.a, b=self.b, ma=self.ma, mb=self.mb, mp=self.mp)
		aonb_2 = v[0][1] / v[1][1]
		print(v)

		a = 5
		b = a/aonb_2

		self.alpha_entry.delete(0, 'end')
		self.beta_entry.delete(0, 'end')
		self.alpha_entry.insert(0, str(a))
		self.beta_entry.insert(0, str(b))

	#~ def modeshapes_link(self):
		#~ webbrowser.open("https://notebooks.azure.com/tjmull/projects/pendulum-lab")

class experiment_window(tk.Toplevel):
	def __init__(self, master):
		tk.Toplevel.__init__(self, master)

		master.experiment_window_open = 1
		self.protocol("WM_DELETE_WINDOW", self.on_closing_experiment_window)

		self.experiment_button = tk.ttk.Button(self, text='Start Countdown', command=lambda:self.experiment())
		self.countdown_n = tk.IntVar()
		self.countdown_n.set('')
		self.countdown_label = tk.Label(self, font=('Helvetica', 18), textvariable=self.countdown_n)

		self.info_icon=tk.PhotoImage(file="info_icon.png")
		self.experiment_info_button = tk.ttk.Button(self, image=self.info_icon, command=lambda:self.show_experiment_message())
		image=self.info_icon

		#~ self.abort_button = tk.ttk.Button(self, text='Abort!', command=lambda:pend.cancel_function()

		self.more_toggle = ToggledFrame(self, text='More Options...', highlightbackground="#ACACAC", highlightcolor="#ACACAC", highlightthickness=1,)#borderwidth=1, bg='#505050')#relief='solid',

		self.show_graph = tk.IntVar()
		self.show_graph.set(0)
		self.anim_graph_checkbutton = tk.Checkbutton(self.more_toggle.sub_frame, text='Show animated graph', variable=self.show_graph)
		self.show_video = tk.IntVar()
		self.show_video.set(1)
		self.video_checkbutton = tk.Checkbutton(self.more_toggle.sub_frame, text='Show video', variable=self.show_video)

		self.duration_entry = tk.ttk.Entry(self.more_toggle.sub_frame, width=4, font=master.master.default_font, validate='key', validatecommand=master.vcmd)
		self.duration_label = tk.ttk.Label(self.more_toggle.sub_frame, text='Duration [s]:')
		self.duration_entry.insert(0, "6")
		self.more_options_info_button = tk.ttk.Button(self.more_toggle.sub_frame, image=self.info_icon, command=lambda:self.show_more_options_info())

		#layout
		padding = master.padding
		self.countdown_label.grid			(row=0, column=0, columnspan=2, **padding)
		self.experiment_button.grid			(row=1, column=0, sticky='W', **padding)
		self.experiment_info_button.grid	(row=1, column=1, sticky='NW', **padding)

		self.more_toggle.grid				(row=2, column=0, columnspan=3, sticky='WE', **padding)
		self.anim_graph_checkbutton.grid	(row=0, column=0, columnspan=3, sticky='W', **padding)
		self.video_checkbutton.grid			(row=1, column=0, columnspan=3, sticky='W', **padding)
		self.duration_label.grid			(row=2, column=0, sticky='E', **padding)
		self.duration_entry.grid			(row=2, column=1, sticky='W', **padding)
		self.more_options_info_button.grid	(row=2, column=2, **padding)

	def on_closing_experiment_window(self):
		self.master.experiment_window_open = 0
		self.destroy()

	def show_experiment_message(self):
		'''popup window that gives more info about the experiment and what each button does'''
		root_experiment_info = tk.Toplevel()
		root_experiment_info.title('Experiment info')

		self.experiment_message = tk.Message(root_experiment_info, width=400, padx=5, pady=5, text='\
The experiment is started using the "Start Countdown" button. When the button is pressed, the countdown will begin from 5. \
When the countdown reaches 0, the pendulum motion should be started. \n\n\
When holding the pendulum, ensure the reflective dots are not obscured.\
')
		self.experiment_message.pack()

	def show_more_options_info(self):
		info_window = tk.Toplevel()
		info_window.title('Experiment options info')
		info_message = tk.Message(info_window, width=400, padx=5, pady=5, text=
'The \'Show animated graph\' checkbox picks whether or not to show a graph drawn next to the video being analysed.\n\n\
The \'Show video\' checkbox selects whether to show the video as it is being analysed.\n\n\
The duration of the recorded video can be changed using the duration entry box.\
')
		info_message.pack()

	def experiment(self):
		'''
		Funcion to record video and plot results

		Subtlety:
		We want the traffic light to change while at the same time, running the video capture and analysis function.
		Have done this by creating a thread to run the other function.
		NB. any tkinter processes MUST BE IN THE MAIN THREAD... so pass the inputs to the function video_analysis as below
		the function of DoublePendulumProgram has been split into two parts. part1 (record_video_and_locate_centre) does not use any tkinter,
		part2, (track_dots_and_plot) uses tkinter to plot the live graph so must be in the main thread'''

		master = self.master
		master.plot_number += 1
		plot_number = master.plot_number
		print('plot number {}'.format(plot_number))

		if self.duration_entry.get() != '':
			duration = int(self.duration_entry.get())
		else:
			duration = maseter.auto_duration
		show_video = self.show_video.get()
		show_graph = self.show_graph.get()

		result_queue = queue.Queue()	#create a queue to pass the results of the new thread created when starting the experiment
		drop = Thread(target=self.video_analysis, args=(duration, show_video, show_graph, result_queue), daemon=True)
		#~ drop.start()					#calls the function video_analysis in a seperate thread, and continues with the main thread.

		#master.info_text.set('Drop the pendulum when green light shows')
		master.update()

		#do the countdown
		for i in range(5, 0, -1):
			self.after(700, self.countdown(i))
			self.update()
			if i == 5:
				drop.start()	#start the other thread that calls video_analysis
		self.after(700, self.countdown('GO!'))
		self.update_idletasks()
		self.after(1000, self.countdown('Recording video'))
		self.update()

		total_frames = result_queue.get()
		centre = result_queue.get()
		rotation = result_queue.get()	#read in the results from the seperate thread
		success = result_queue.get()

		self.countdown('Analysing video')
		self.update()

		print('total frames is {}'.format(total_frames))
		answer = True
		if not success:
			answer = messagebox.askyesno("Error","Cannot locate centre, ensure cross-hairs are visible. \n\
Would you like to proceed with a best guess of where the centre might be \
(warning: may be innacurate)?")
			cv2.destroyAllWindows()

		if answer:
			#master.info_text.set('Analysing video')

			time_, alpha, beta, modeshape, resonance = pend.track_dots_and_plot(total_frames, centre, rotation,
				video_length=duration, show_video=show_video, show_graph=show_graph, view_fourier=master.small_angle_table_1.view_fourier.get())
			time_, alpha, beta = pend.find_start_points(time_, alpha, beta)				#adjust zero time

			master.store_data(time_, alpha, beta, 'Experiment'+str(plot_number))			#add data to the store
			master.write_to_csv(time_, alpha, beta, modeshape, resonance, n=plot_number, exp_type='Experiment')

			#master.info_text.set('New experiment plotted')
			g = master.master.graph_area 	#locate the instance of graph area that was initially created.
			g.update_graph(g.fig, plot_number=plot_number, t=time_, a=alpha, b=beta,
									legend_a='Experiment'+str(plot_number), legend_b=' ')
			g.plot_graph(g.fig)

		self.countdown('')
		self.lift()	#make sure window does not dissapear behind other windows.
		self.focus_force()
		if modeshape is not None and resonance is not None:
			master.small_angle_table_1.innards.show_modeshape_text(modeshape, resonance)

	def video_analysis(self, duration, show_video, show_graph, result_queue):
		'''Called as a seperate thread to record a video of the pendulum and
		start the analysis by locating the cross hairs'''
		time.sleep(0.5)
		total_frames, centre, rotation, success = pend.record_video_and_locate_centre(video_length=duration,
			show_video=show_video, show_graph=show_graph) # t, a and b are three lists
		result_queue.put(total_frames)
		result_queue.put(centre)
		result_queue.put(rotation)
		result_queue.put(success)
		return

	def countdown(self, n):
		self.countdown_n.set(n)

class small_angle_table(tk.Frame):
	def __init__(self, master):
		tk.Frame.__init__(self, master)
		self.frame = tk.LabelFrame(self, text='Small Angles')
		padding = master.padding

		#~ self.frame.grid_rowconfigure(0, weight=1)
		#~ self.frame.grid_columnconfigure(0, weight=1)

		self.yscrollbar = tk.ttk.Scrollbar(self.frame)
		self.canvas = tk.Canvas(self.frame, bd=0, width=262, height=150,
						yscrollcommand=self.yscrollbar.set)
		self.view_fourier = tk.IntVar()
		self.view_fourier.set(0)
		self.view_fourier_checkbutton = tk.Checkbutton(
			self.frame, text='View fourier transform', variable=self.view_fourier)

		self.calculate_modes_button = tk.ttk.Button(self.frame, text='Calculate mode shapes...', command=lambda:modeshapes_link())

		self.yscrollbar.grid(row=2, column=1, sticky='NS')
		self.canvas.grid(row=2, column=0, sticky='NSEW', **padding)
		self.view_fourier_checkbutton.grid(row=0, column=0, columnspan=2, sticky='W',)
		self.calculate_modes_button.grid(row=1, column=0, columnspan=2, sticky='WE', **padding)

		self.yscrollbar.configure(command=self.canvas.yview)

		self.innards = small_angle_table_innards(self.canvas)

		self.canvas.create_window((0,0), window=self.innards, anchor='nw')
		self.canvas.configure(scrollregion=self.canvas.bbox("all"))

		self.frame.pack(fill='both', expand=True)


class small_angle_table_innards(tk.Frame):
	def __init__(self, master):
		#long winded, but no easier way to make a table I don't think
		self.boarders = {'borderwidth':1, 'relief':'solid'}
		tk.Frame.__init__(self, master, **self.boarders)

		self.number_ = tk.ttk.Label(self, text='Expt.\nno.', **self.boarders)
		self.modeshape = tk.ttk.Label(self, text='Modeshape', **self.boarders)
		self.resonant_frequency = tk.ttk.Label(self, text='Resonant\nFrequency', **self.boarders)
		self.alphabeta = tk.ttk.Label(self, text='[\u03b1/\u03b2]', **self.boarders)
		self.Hz = tk.ttk.Label(self, text='[Hz]', **self.boarders)
		self.empty_label = tk.ttk.Label(self, text='', **self.boarders)

		self.number_.grid			(row=0, column=0, sticky='NSEW', ipadx=5)
		self.modeshape.grid			(row=0, column=1, sticky='NSEW', ipadx=5)
		self.resonant_frequency.grid(row=0, column=2, sticky='NSEW', ipadx=5)
		self.empty_label.grid		(row=1, column=0, sticky='NSEW', ipadx=5)
		self.alphabeta.grid			(row=1, column=1, sticky='NSEW', ipadx=5)
		self.Hz.grid				(row=1, column=2, sticky='NSEW', ipadx=5)

	def show_modeshape_text(self, modeshape, resonance):
		main_page = self.master.master.master.master
		plot_number = main_page.plot_number
		c,r = self.grid_size()

		self.plot_number_entry = tk.ttk.Label(self, text=str(plot_number), **self.boarders)
		self.modeshape_entry = tk.ttk.Label(self, text='{:.2f}'.format(modeshape), **self.boarders)
		self.resonance_entry = tk.ttk.Label(self, text='{:.2f}'.format(resonance), **self.boarders)

		self.plot_number_entry.grid (row=r, column=0, sticky='NSEW', ipadx=5)
		self.modeshape_entry.grid	(row=r, column=1, sticky='NSEW', ipadx=5)
		self.resonance_entry.grid	(row=r, column=2, sticky='NSEW', ipadx=5)

		size = list(self.master.bbox('all'))
		size[3] += 27			#add the space of an extra box onto the bottom of the bounding box so the
								#most recent row of data is visible when you scroll to the bottom
		self.master.configure(scrollregion=size)		#self.master is 'canvas' created in small_angle_table


class step1(tk.Frame):
	def __init__(self, master):
		tk.Frame.__init__(self, master)

		##############NEEDS NEATENTING UP#################

		self.experiment_window_open = 0
		self.simulation_window_open = 0
		self.auto_duration = 6		#default length of test of 6 seconds

		self.step_number = 0
		self.plot_number = 0
		self.text_width = 450
		self.padding = {'padx': '3', 'pady': '3'}
		self.vcmd = (self.register(self.validate),'%P', '%S', '%d') #for reference, here is what the % signs mean: %d Type of action: 1 for insert, 0  for  delete,  or  -1  for  focus,forced or textvariable validation. %i   Index of char string to be inserted/deleted, if any, otherwise -1.%P   The value of the entry if the edit is allowed.  If you are config-uring  the  entry  widget to have a new textvariable, this will be the value of that textvariable. %s The current value of entry prior to editing. %S The text string being inserted/deleted, if any, {} otherwise.%v   The type of validation currently set.%V   The type of validation that triggered the callback (key,  focusin,focusout, forced). %W The name of the entry widget.

		#~ self.instruction_text = tk.StringVar()
		#~ self.set_instruction_message()
		#~ self.instruction_message = tk.Message(self, width=500, textvariable=self.instruction_text)
		#~ self.next_button = tk.ttk.Button(self, text='Next', command=lambda:self.next_step())
		#~ self.back_button = tk.ttk.Button(self, text='Back', command=lambda:self.back_step())

		#~ #left side
		self.clear_button = tk.ttk.Button(self, text='Clear graph', command=lambda:self.clear())
		#~ self.info_text = tk.StringVar()
		#~ self.info_text.set('')
		#~ self.info_message = tk.Message(self, width=400, borderwidth=2, relief='groove', textvariable=self.info_text) #width=self.text_width,
		#~ self.simul_frame = simulate_frame(self)
		#~ #right side
		#~ self.exp_frame = experiment_frame(self)
		#~ self.duration_entry = tk.ttk.Entry(self, width=4, font=master.default_font, validate='key', validatecommand=self.vcmd)
		#~ self.duration_label = tk.ttk.Label(self, text='Duration [s]:')
		self.remove_line_button = tk.ttk.Button(self, text='Remove previous line', command=lambda:self.remove_line())

		#~ #Diagram
		photo = tk.PhotoImage(file="DoublePendulumDiagram.gif")
		self.diagram = tk.Label(self, image=photo)
		self.diagram.image = photo

		#~ #to the right of the diagram
		self.send_results_button = tk.ttk.Button(self, text='Send results by email', command=lambda:self.send_results())
		self.intro_page_button = tk.ttk.Button(self, text='Intro screen', command=lambda:master.make_intro_frame(master.master))
		self.small_angle_table_1 = small_angle_table(self)

		#~ #layout********************************************************
		padding = self.padding

		#~ #left side
		#~ self.instruction_message.grid	(row=0, column=0, columnspan=4, sticky='W', **padding)
		#~ self.next_button.grid			(row=0, column=7, sticky='W', **padding)
		#~ self.back_button.grid			(row=0, column=5, sticky='E', **padding)
		#~ self.simul_frame.grid			(row=2, column=0, columnspan=3, sticky='NSEW', **padding)
		#~ self.duration_label.grid		(row=3, column=0, sticky='E', **padding)
		#~ self.duration_entry.grid		(row=3, column=1, sticky='EW', **padding)
		self.clear_button.grid			(row=3, column=0, sticky='SE', **padding)
		self.remove_line_button.grid	(row=3, column=1, sticky='SW', **padding)

		#~ #right side - Experiment
		#~ self.exp_frame.grid					(row=2, column=3, columnspan=4, sticky='NSEW', **padding)
		#~ self.info_message.grid				(row=3, column=4, columnspan=5, sticky='NSEW', **padding)

		#~ #Diagram
		self.diagram.grid				(row=0, column=9, rowspan=4, **padding)

		#~ #right of the diagram
		self.send_results_button.grid	(row=0, column=11, **padding)
		self.intro_page_button.grid		(row=0, column=10, **padding)
		self.small_angle_table_1.grid	(row=2, column=10, columnspan=2, sticky='W', **padding)
		#~ self.duration_entry.insert(0, '6')				#the validate function updates the info_text

		#~ #self.columnconfigure(0, minsize=self.text_width)

		#***********************************************

		self.simulation_button = tk.ttk.Button(self, text='Simulation', command=lambda:self.show_simulation_window())
		self.experiment_button = tk.ttk.Button(self, text='Experiment', command=lambda:self.show_experiment_window())

		#layout*******************************************

		self.simulation_button.grid		(row=0, column=0, rowspan=3, sticky='EW', **padding)
		self.experiment_button.grid		(row=0, column=1, rowspan=3, sticky='EW', **padding)

	def show_experiment_window(self):
		if self.experiment_window_open == 1:
			print('Experiment window already open')
			self.exp_window.lift()
		else:
			self.exp_window = experiment_window(self)

	def show_simulation_window(self):
		if self.simulation_window_open == 1:
			print('Simulation window already open')
			self.simul_window.lift()
		else:
			self.simul_window = simulation_window(self)

	def back_to_intro(self):
		print('back to intro')

	def next_step(self):
		if self.step_number != 2:
			self.step_number +=1
		self.set_instruction_message()

	def back_step(self):
		if self.step_number != 0:
			self.step_number -=1
		self.set_instruction_message()

	def set_instruction_message(self):
		if self.step_number == 0:
			self.instruction_text.set('1. Introduction\nTo begin, drop the pendulum from an angle \u03b1=90\u00b0 and \u03b2=0\u00b0. \
Do this three times. Then run a simulation with the same starting conditions. Compare the results using the plot. ')
		elif self.step_number == 1:
			self.instruction_text.set('2. Small Angles\nWhen \u03b1 and \u03b2 are small, the system can be approximated linearly. \
This leads to a model with two modes of vibration. Try to find each and plot them on the graph. Compare with simulations.')

		elif self.step_number == 2:
			self.instruction_text.set('3. Further Investigation\n\
Run the first experiment again, but this time use your own starting conditions. \
Does the resulting graph have similar behaviour? Are there certain starting angles that produce \
different behaviour? ')


	def validate(self, value_if_allowed, text, action):	#validates the entry to the alpha and beta boxes. returns true if entry allowed
		#self.info_text.set('')
		if(action=='1'):
			if all(t in '0123456789.-+' for t in list(text)):	#only accept numbers and .+- (use all() command since numbers may come in as two digit strings)
				try:
					if abs(float(value_if_allowed)) > 180:
						#self.info_text.set('Angle must be between -180 and 180')
						return False
					else:
						return True
				except ValueError:
					if value_if_allowed == '-':
						return True
					else:
						return False
			else:
				return False
		else:
			return True

	def remove_line(self):
		g = self.master.graph_area

		line = g.ax1.lines[-1]		#get the last line in the list of lines
		line.remove()				#and delete it
		line = g.ax2.lines[-1]
		line.remove()

		g.update_graph(g.fig)
		g.plot_graph(g.fig)
		#self.plot_number -= 1
		print('removing one line')

	def clear(self):
		'''delete all lines plotted so far'''
		g = self.master.graph_area

		l1 = [i for i in g.ax1.lines]		#create a copy of g.ax1.lines that does not reference it... otherwise you cannot iterate over it, since you are deleting its entries as you go
		l2 = [i for i in g.ax2.lines]
		for line in l1:
			line.remove()
		for line in l2:
			line.remove()

		g.ax1.legend(loc='center left', bbox_to_anchor=(1, 0.5))
		g.ax2.legend(loc='center left', bbox_to_anchor=(1, 0.5))

		g.plot_graph(g.fig)
		#self.plot_number = 0

	def store_data(self, t, a, b, name):
		t_global.append(t)
		a_global.append(a)
		b_global.append(b)
		name_global.append(name)

	def write_to_csv(self, t, a, b, m='None', r='None', n=0, exp_type='Drop'):
		global crsids
		#~ crsids = self.master.intro_frame.crsids		get crsids from when they were entered.
		file_names = [str(crsid)+'.csv' for crsid in crsids]
		folder_name = 'Double Pendulum Lab Data'

		for file_name in file_names:

			file_location = os.path.join(folder_name, file_name)

			try:
				with open(file_location, 'a', newline='') as f:
					writer = csv.writer(f)

					t = list(t)
					a = list(a)
					b = list(b)

					writer.writerow(['{}. {}'.format(n, exp_type)])
					writer.writerow(['Time [s]'] + t)
					writer.writerow(['Alpha [deg]'] + a)
					writer.writerow(['Beta [deg]'] + b)
					writer.writerow(['Mode shape [alpha/beta]', m])
					writer.writerow(['Resonant Frequency [Hz]', r])
					writer.writerow('')

			except FileNotFoundError:
				try:
					os.makedirs(folder_name)
				except FileExistsError:
					tk.messagebox.showinfo("Error", "File not found to write results to, new one has now been created. Try again")
					print('File not found, new one has been created. Try again')

	def send_results(self):
		global crsids
		messagebox.showinfo('Send Results by email', 'Sending results to the following crsids: {}'.format(', '.join(crsids)))

		with open('.DoublePendulum.email') as gmail_info:
			gmail_username = gmail_info.readline().strip()
			gmail_password = gmail_info.readline().strip()

		for crsid in crsids:
			message = 'Dear {}\n\n\
Attached are your results from the IB double pendulum lab. \n\n\
They are contained in an csv file, which can be opened by most programs including excel. \n\n\
All the best, \n\n\
Double Pendulum Lab'.format(crsid)
			file_location = os.path.join('Double Pendulum Lab Data', crsid+'.csv')
			try:
				send_mail(gmail_username+'@gmail.com', crsid+'@cam.ac.uk', 'Double Pendulum Lab Results',
						message, file_location, server='smtp.gmail.com', port=587, username=gmail_username,
						password=gmail_password)
				messagebox.showinfo('Send Results by email', 'Data sent successfully to {}@cam.ac.uk!'.format(crsid))
				os.remove(file_location)	#clears up after itself if email is sent successfully
			except Exception as e:
				messagebox.showerror("Error", e)

def send_mail(send_from, send_to, subject, message, file_location='',
			  server="localhost", port=587, username='', password='',
			  use_tls=True):
	"""Compose and send email with provided info and attachment.

	Args:
		send_from (str): from name
		send_to (str): to name
		subject (str): message title
		message (str): message body
		file_location (str): file path to be attached to email
		server (str): mail server host name
		port (int): port number
		username (str): server auth username
		password (str): server auth password
		use_tls (bool): use TLS mode
	"""
	msg = MIMEMultipart()
	msg.attach(MIMEText(message, 'plain'))

	part = MIMEBase('application', 'octet-stream')
	with open(file_location, 'rb') as attachment:
		part.set_payload((attachment).read())
	encoders.encode_base64(part)
	part.add_header('Content-Disposition', 'attachment; filename={}'.format(os.path.basename(file_location)))
	msg.attach(part)

	msg['From'] = send_from
	msg['To'] = send_to
	msg['Date'] = formatdate(localtime=True)
	msg['Subject'] = subject

	smtp = smtplib.SMTP(server, port)
	if use_tls:
		smtp.starttls()
	smtp.login(username, password)
	smtp.sendmail(send_from, send_to, msg.as_string())
	smtp.quit()


class main_window(tk.Frame):
	def __init__(self, master):
		tk.Frame.__init__(self, master)
		master.title('Double Pendulum Experiment')
		try:
			master.state('zoomed')						#maximise the window using windows
		except:
			master.wm_attributes('-zoomed', 1)			#maximise on rpi linux

		self.default_font = tk.font.nametofont("TkDefaultFont")#change default font size
		self.default_font.configure(size=13)

		self.make_intro_frame(master)

	def make_intro_frame(self, master):

		for w in self.winfo_children():
			w.destroy()

		self.intro_frame = intro_stream(self)
		self.intro_frame.pack(fill='y', expand=True)

	def make_main_frame(self):

		self.graph_area = graph_area(self)
		self.step = step1(self)

		self.step.pack(fill='both', expand=True, anchor='n')
		self.graph_area.pack(fill='both', expand=True, anchor='s')


class intro_stream(tk.Frame):
	def __init__(self, master):
		tk.Frame.__init__(self, master)

		self.padding = {'padx': '3', 'pady': '3'}
		padding = self.padding
		self.w, self.h = 720, 720
		global crsids
		self.crsids = crsids

		self.vcmd = (self.register(self.validate),'%P', '%S', '%d')
		# %P The value of the entry if the edit is allowed,
		# %S The text string being inserted/deleted, if any, {} otherwise.
		# %d Type of action: 1 for insert, 0  for  delete,  or  -1  for  focus,forced or textvariable validation.

		self.preview_frame = tk.Frame(self, width=self.w , height=self.h, bg='red')	#frame that fills screen space so that the button is in the right place (under the preview)

		self.preview_message = tk.Message(self, width=self.w, text=\
'Note that the two reflective circles on the pendulum arms should be visible to the camera \
for the duration of the experiment\n\n\
Please enter your CRSIDs so that your experimental data can be stored\n')

		self.continue_button = tk.ttk.Button(self, text='Continue', command=lambda:self.continue_button_press())
		self.crsid_entry = tk.ttk.Entry(self, width=7, font=master.default_font, validate='key',
																		validatecommand=self.vcmd)
		self.crsid_label = tk.ttk.Label(self, text='Enter CRSIDs:')
		self.crsid_button = tk.ttk.Button(self, text='Enter', command = lambda:self.add_crsid())
		self.entered_crsids = tk.StringVar()
		self.entered_crsids.set('')
		self.entered_crsids_label = tk.ttk.Label(self, textvariable=self.entered_crsids)
		self.remove_crsid_button = tk.ttk.Button(self, text='Undo', command=lambda:self.remove_crsid())

		self.preview_frame.grid		(row=0, column=0, columnspan=5)
		self.preview_message.grid	(row=1, column=0, columnspan=5)
		self.crsid_label.grid		(row=2, column=0, sticky='E', **padding)
		self.crsid_entry.grid		(row=2, column=1, sticky='WE', **padding)
		self.crsid_button.grid		(row=2, column=2, sticky='WE', **padding)
		self.remove_crsid_button.grid(row=2, column=3, sticky='E', **padding)
		self.continue_button.grid	(row=2, column=4, **padding)
		self.entered_crsids_label.grid(row=3, column=1, sticky='W', **padding)

		self.update_idletasks()
		self.loc = master.master.winfo_geometry()
		self.loc = self.loc.split('x')
		self.loc = [self.loc[0]] + self.loc[1].split('+')		#split up the output of winfo_geometry (format of 'wxh+x+y')
		self.y = int(self.loc[3])
		self.x = (int(self.loc[0]) - self.w) // 2		#little equation to centre the preview onscreen

		self.show_preview()

	def validate(self, value_if_allowed, text, action):	#validates the entry to the crsid box
		if(action=='1'):
			if text in 'qwertyuiopasdfghjklzxcvbnm1234567890': #letters and numbers only
				return True
			else:
				return False
		else:
			return True

	def remove_crsid(self):
		if self.crsids:			#if crsids is not empty
			del self.crsids[-1]
			self.display_crsids()

	def add_crsid(self):
		self.crsid = self.crsid_entry.get()

		if self.crsid not in self.crsids and self.crsid != '':
			self.crsids.append(self.crsid)
		self.display_crsids()

	def display_crsids(self):
		self.crsid_entry.delete(0, 'end')
		r = ''
		for c in reversed(self.crsids):	#display most recent entry at the top of the list
			r = r + str(c) + '\n'

		self.entered_crsids.set(r)

	def show_preview(self):
		try:
			self.camera = picamera.PiCamera()

			self.camera.resolution = (self.w, self.h)
			self.camera.framerate = 30
			self.camera.shutter_speed = 1500
			self.preview = self.camera.start_preview()
			self.preview.fullscreen = False
			self.preview.window = (self.x, self.y, self.h, self.w)

			img = Image.open('preview_overlay.png')
			pad = Image.new('RGBA', (
				((img.size[0] + 31) // 32) * 32,
				((img.size[1] + 15) // 16) * 16,
				))
			pad.paste(img, (0, 0))

			self.overlay = self.camera.add_overlay(pad.tobytes(), size=img.size)
			self.overlay.layer = 3
			self.overlay.fullscreen = False
			self.overlay.window = (self.x, self.y, self.h, self.w)

		except Exception as e:
			print(e)

	def continue_button_press(self):
		self.add_crsid()	#if there is a crsid in the box, but they forgot to press enter, then add it to the list anyway
		try:
			self.camera.stop_preview()
			self.camera.close()
		except Exception as e:
			print(e)

		self.destroy()
		self.master.make_main_frame()

def on_closing():
    if messagebox.askokcancel("Quit", "Do you want to quit?"):
        root.destroy()

if __name__ == '__main__':
	root = tk.Tk()
	top_frame = main_window(root)				#frame that holds whole program
	top_frame.pack(fill="both", expand=True) 	#fill the window with this frame

	root.protocol("WM_DELETE_WINDOW", on_closing)
	root.mainloop()
