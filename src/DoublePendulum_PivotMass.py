import numpy as np
from scipy import linalg
import matplotlib.figure
import matplotlib.animation as animation
import argparse
import time
from DoublePendulumProgram import small_angles


from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
import matplotlib
matplotlib.use('TkAgg')

class DoublePendulum:

	def __init__(self, a, b, mp, ma=None, mb=None, *, g=9.81):
		self.a = a
		self.b = b

		if ma is None:
			self.ma = a
		else:
			self.ma = ma

		if mb is None:
			self.mb = b
		else:
			self.mb = mb

		self.mp = mp

		self.g = g

	def matvec(self, alpha, beta, alphadot, betadot):
		m = self.mb / self.ma
		m2 = self.mp / self.ma
		l = self.b / self.a
		cab = np.cos(alpha - beta)
		sab = np.sin(alpha - beta)

		mat = np.array([[
			(2 + 6*m + 6*m2) / l,
			3 * m * cab
		],[
			3 * m * cab,
			2 * m * l
		]])

		vec = np.array([(
			-3 * m * betadot**2 * sab -
			(3 + 6*m + 6*m2) * (self.g / self.b) * np.sin(alpha)
		),(
			3 * m * alphadot**2 * sab -
			3 * m * (self.g / self.a) * np.sin(beta)
		)])

		return mat, vec

	def accels(self, alpha, beta, alphadot, betadot):
		mat, vec = self.matvec(alpha, beta, alphadot, betadot)
		a1, a2 = np.linalg.solve(mat, vec)
		return np.array([alphadot, betadot, a1, a2])

	def coords(self, alpha, beta):
		x0 = 0
		y0 = 0
		x1 = x0 + self.a * np.sin(alpha)
		y1 = y0 - self.a * np.cos(alpha)
		x2 = x1 + self.b * np.sin(beta)
		y2 = y1 - self.b * np.cos(beta)
		return [x0, x1, x2], [y0, y1, y2]

	def energy(self, alpha, beta, alphadot, betadot):
		return (
			self.ma * self.a**2 * alphadot**2 / 6 + self.mp*self.a**2*alphadot**2 / 2   #KE arm1
		  - (self.ma/2 + self.mp) * self.g * self.a * np.cos(alpha)                     #PE arm1
		  + self.mb * (                                                                 #arm2 stuff
				self.a**2 * alphadot**2
			  + self.b**2 * betadot**2 / 3
			  + self.a * self.b * alphadot * betadot * np.cos(alpha-beta)
			) / 2
		  - self.mb * self.g * (
				self.a * np.cos(alpha)
			  + self.b * np.cos(beta) / 2
			)
		)

	def range(self):
		l = self.a + self.b
		return -l, l

	def eigen(self):
		#This is John's way which I think I ruined when I hijacked it, so I've just done it again below
		#~ m = self.mb / self.ma
		#~ m2 = self.mp / self.ma
		#~ l = self.b / self.a

		#~ M = np.array([[
			#~ (2+6*m+6*m2)/(3+6*m+6*m2),
			#~ m*l/(1+2*m)
		#~ ],[
			#~ 1,
			#~ 2*l/3
		#~ ]])
		#~ val, vec = np.linalg.eig(M)

		a = self.a
		b = self.b
		ma = self.ma
		mb = self.mb
		mp = self.mp
		g = self.g

		M = np.array([[ (1/3*ma+mb+mp)*a**2 , 0.5*mb*a*b ],
              [ 0.5*mb*a*b          , 1/3*mb*b**2]])

		K = np.array([[ (0.5*ma+mb+mp)*g*a , 0         ],
					  [ 0                  , 0.5*mb*g*b]])

		val, vec = linalg.eig(K, M)

		return val, vec

	def printmode(self, val, vec):
		period = 2 * np.pi * np.sqrt(val * self.a / self.g)
		print('{:.3f} s, {:.3f} Hz, shape [{:.3f} {:.3f}]'.format(period, 1/period, vec[0], vec[1]))


def direction(c):
	i = 'uldr'.find(c)
	if i >= 0:
		return (i-2)*np.pi/2
	else:
		return None

def find_mode(a=1.0, ma=1.0, b=0.8, mb=0.8, mp=0):
	p = DoublePendulum(a=a, b=b, mp=mp, ma=ma, mb=mb)

	val, vec = p.eigen()

	return vec



def run(a=1.0, adot=0, ma=1.0, b=0.8, bdot=0, mb=0.8, mp=0, dt=0.02,
		alpha=None, beta=None, ni=None, anim=True, graph=False, length=3, view_fourier=True):

	p = DoublePendulum(a, b, mp, ma, mb)

	#define variables
	alphadot = np.deg2rad(adot)
	betadot = np.deg2rad(bdot)
	t = 0
	t_total = length				#length of simulation
	i_max = round(t_total//dt)		#number of iterations


	#initialise alpha/beta values
	if alpha is not None:
		alpha = np.deg2rad(alpha)
		if beta is not None:
			beta = np.deg2rad(beta)
		else:
			beta = 0
	else:
		if ni is None:
			alpha = np.random.uniform(-np.pi, np.pi)
			beta = np.random.uniform(-np.pi, np.pi)
		else:
			try:
				val, vec = p.eigen()

				i = int(ni)
				alpha = vec[0,i] / 5
				beta = vec[1,i] / 5

				ax.plot(*p.coords(alpha, beta))
				p.printmode(val[i], vec[i])
			except ValueError:
				alpha = direction(ni[0])
				beta = direction(ni[1])

	#initiate the lists with a string of the first value times n to make them more similar to experimental data
	n = 50
	alpha_list = [np.rad2deg(alpha)]*n
	beta_list = [np.rad2deg(beta)]*n

	def RK4(alpha, beta, alphadot, betadot):
		'''
		runge kutta 4th order
		'''
		#4th order Runge-Kutta
		y = np.array([alpha, beta, alphadot, betadot])

		k1 = p.accels(*y)
		k2 = p.accels(*(y + dt*k1/2))
		k3 = p.accels(*(y + dt * k2 / 2))
		k4 = p.accels(*(y + dt * k3))

		# compute the RK4 right-hand side
		R = 1.0 / 6.0 * dt * (k1 + 2.0 * k2 + 2.0 * k3 + k4)

		# update the angles and angular velocities
		alpha += R[0]
		beta += R[1]
		alphadot += R[2]
		betadot += R[3]

		return alpha, beta, alphadot, betadot

	if anim:
		fig_anim = matplotlib.figure.Figure()
		ax = fig_anim.subplots()
		ax.set_xlim(p.range())
		ax.set_ylim(p.range())
		ax.set_aspect('equal', adjustable='box')

		line, = ax.plot(*p.coords(alpha, beta))

		t_text = ax.text(0.01, 0.99, 'Time: {:.3f}'.format(t),
			horizontalalignment='left',
			verticalalignment='top',
			transform = ax.transAxes
		)

		e_text = ax.text(0.99, 0.99, 'Energy: {:.3f}'.format(p.energy(alpha, beta, alphadot, betadot)),
			horizontalalignment='right',
			verticalalignment='top',
			transform = ax.transAxes
		)
		start = time.process_time() 	#used for animation speed limiter
		end = time.process_time()

		def animate(i):
			nonlocal alpha, beta, alphadot, betadot, t, start, end

			while end - start < 0.01:		#sets limit on the max speed animation shows at
				end = time.process_time()
			start = time.process_time()

			alpha, beta, alphadot, betadot = RK4(alpha, beta, alphadot, betadot)

			t+=dt
			na = (alpha+np.pi)//(2*np.pi)		#find the absolute number of rotations each arm has made and modify angle to be within reange -180 to +180 deg
			alpha_list.append(alpha/2/np.pi*360 - na*360)
			nb = (beta+np.pi)//(2*np.pi)
			beta_list.append(beta/2/np.pi*360 - nb*360)

			line.set_data(*p.coords(alpha, beta))
			t_text.set_text('Time: {:.3f}'.format(t))
			e_text.set_text('Energy: {:.3f}'.format(p.energy(alpha, beta, alphadot, betadot)))


			if i == i_max - 1:
				nonlocal pause_here
				pause_here = 0

			return line, t_text, e_text

		root2 = tk.Toplevel()			#plotting the animation in a seperate tkinter window is the cleanest way to show the simulation that I have found
		root2.title("Double Pendulum Simulation")
		canvas = FigureCanvasTkAgg(fig_anim, master=root2)
		canvas.get_tk_widget().pack()

		pause_here = 1

		ani = animation.FuncAnimation(fig_anim, animate, interval=1, blit=True, frames=i_max, repeat=False)

		root2.update()

		while pause_here:
			root2.update()

		root2.destroy()

		t_list = np.arange(0,len(alpha_list)*dt,dt)

	else:
		for i in range(i_max):
			alpha, beta, alphadot, betadot = RK4(alpha, beta, alphadot, betadot)
			na = (alpha+np.pi)//(2*np.pi)		#find the absolute number of rotations each arm has made and modify angle to be within reange -180 to +180 deg
			alpha_list.append(alpha/2/np.pi*360 - na*360)
			nb = (beta+np.pi)//(2*np.pi)
			beta_list.append(beta/2/np.pi*360 - nb*360)
			t_list = np.arange(0,len(alpha_list)*dt,dt)
		if graph:
			plt.plot(t_list, alpha_list, t_list, beta_list)
			plt.show()
			print('this should not happen')

	if max(alpha_list) < 45 and max(beta_list) < 90:
		modeshape, resonance = small_angles(t_list, alpha_list, beta_list, fps=1/dt, view_graph=view_fourier)
	else:
		modeshape, resonance = None, None

	return t_list, alpha_list, beta_list, modeshape, resonance

def main():
    run()

if __name__ == '__main__':
    main()
