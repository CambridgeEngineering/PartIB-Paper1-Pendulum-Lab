import cv2
import numpy as np
try:
	import picamera			#if running on computer not connected to camera
except Exception as e:
	print(e)
import os
import matplotlib
import tkinter as tk
from tkinter import messagebox
import matplotlib.animation as anim
import time
import DoublePendulum_PivotMass as simulation
import PIL.Image, PIL.ImageTk

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

filename = 'Double_pendulum'
file_type = '.h264'

global cancel
cancel = False

def record_video(video_length, width, height, fps):
	'''
	Args:
		filename (str):
			name of file to be created (without extension).
		video_length (int):
			length of video (seconds)
	'''
	try:
		with picamera.PiCamera() as camera:
			camera.resolution = (width, height)
			camera.framerate = fps
			camera.shutter_speed = 1500
			camera.iso = 800
			time.sleep(2.1)
			camera.start_recording(filename + file_type)
			camera.wait_recording(video_length)
			camera.stop_recording()
			print('iso: {}'.format(camera.iso))
			print('brightness: {} \ndigital_gain: {}\nanalog_gain: {}\nexposure_compensation:\
{}\nexposure_mode {}\nexposure_speed: {}\nimage_effect: {}\nsensor_mode :{}'.format(camera.brightness, camera.digital_gain,
camera.analog_gain, camera.exposure_compensation, camera.exposure_mode, camera.exposure_speed, camera.image_effect,
camera.sensor_mode))
	except Exception as e:
		print(e)


def init_frame_extraction():
	'''
	Args: where to get file from
	Return: cap - a VideoCapture object set to extract frames from the file selected
	'''
	# Create a VideoCapture object and read from input file
	cap = cv2.VideoCapture(filename + file_type)
	if (cap.isOpened()== False): 					# Check if camera opened successfully
		print("Error opening video file")
	return cap

def extract_next_frame(cap):
	'''
	Input:
		cap:
			The VideoCapture object holding the location of the video file
	Output:
		img:
			An image of the next frame of the video, None if the video has reached the last frame
	'''
	ret, img = cap.read()	#read next frame
	if ret == True:
		return img			#if it read successfully, then return the image
	else:
		print('Video Finished')
		cap.release() 		#When the last frame is reached, release the video capture object and output 'None'
		return None


def find_centre(img):
	'''
	Args:
		img (ndarray):
			image to find the centre of
	Return:
		centre (x,y):
			Coords of the estimated centre of the image
		rotation (float):
			amount of rotation to get from inital to proper coords (deg) anticlkwse +ve
			amount of rotation to get from inital to proper coords (deg) anticlkwse +ve
	'''
	gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)		#change image to greyscale
	retval, thresh = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY) #threshold the image

	#crop to central portion of the image (cropped image has side dims 1/4 of full image)
	width = thresh.shape[1]
	height = thresh.shape[0]
	topleft = (width*3//8, height*3//8)
	botright = (width*5//8, height*5//8)
	cropped = thresh[topleft[1]:botright[1], topleft[0]:botright[0]]	#crop the grayscale image
	cropped_img = img[topleft[1]:botright[1], topleft[0]:botright[0]]	#crop the colour image as well for display purposes

	#show result of thresholding
	#~ cv2.imshow("Keypoints", cropped)
	#~ cv2.waitKey(300)

	#use HoughLinesP algorithm to detect the cross-hairs
	lines = None
	#lines will be a list of lists. each list will contain a start and end point x1,y1 and x2,y2
	lines = cv2.HoughLinesP(image=cropped, rho=1, theta=np.pi/180, threshold=50, minLineLength=10, maxLineGap=200) #rho is resolution of 1 pixel, theta is resolution of 1 degree
	if lines is not None:

		#find gradient, m and intercept, c for each line and extract the best two lines that are greater than 45deg different. let them be at the indexed points 0 and 1
		all_angle = []	#holds angles for all lines found
		all_c = []
		angle = [0, 0]	#holds anlges for only the lines used (one vertical, one horizontal)
		c = [0, 0]
		for i in range(len(lines)):
			for x1,y1,x2,y2 in lines[i]:
				if x2-x1 == 0:
					all_angle.append(np.pi/2)						#if line is vertical, angle is 90deg = pi/2
					all_c.append(x1)								#there is no intercept, so in this special case, set the intercept as the x intercept rather than the y intercept
				else:
					all_angle.append(np.arctan((y2-y1)/(x2-x1))) 	#convert two endpoints of a line to it's angle wrt horizontal (+ve angles downward (sorry))
					all_c.append((y1*x2-x1*y2)/(x2-x1))				#work out the y-intercept for line above
			if abs(abs(all_angle[0]) - abs(all_angle[i])) > np.pi/4:	#find the first i that has angle difference greater than 45deg
				angle[0] = all_angle[0]
				angle[1] = all_angle[i]
				c[0] = all_c[0]							#set that one as index 1
				c[1] = all_c[i]
				i2 = i
				break
		print('angle1 {}, c1 = {}; angle2 = {}, c2 = {}'.format(angle[0], c[0], angle[1], c[1]))

		if c[1] == 0:	#if two perpendicular lines have not been found, unsuccessful
			success = False
		else:
			success=True

			#locate centre point (intercept between the lines)
			#~ for i in [0, second_line_i]:

			if angle[0] == 0:			#if 1st line is perfectly horizontal,
				y_centre = c[0]			#y value is the intercept
			elif angle[1] == 0: # also if 2nd line is horizontal
				y_centre = c[1]
			else:
				y_centre = (np.tan(angle[0])*c[1] - np.tan(angle[1])*c[0]) / (np.tan(angle[0]) - np.tan(angle[1]))

			if angle[0] == np.pi/2:	#special case: line vertical
				x_centre = c[0]			#c is now the x intercept
			elif angle[1] == np.pi/2:
				x_centre = c[1]
			else:				#line at any other angle
				x_centre = (c[1]-c[0])/(np.tan(angle[0]) - np.tan(angle[1]))

			centre = (int(round(x_centre)),int(round(y_centre)))

			#find the angle that rotates image to vertical (anticlkwse +ve)
			for i in range(2):
				if abs(angle[i] - np.pi/2) < 0.35:			#if angle is near +-90, then add or subtract 90deg to get the correct small correction angle.
					angle[i] = angle[i] - np.pi/2
				if abs(angle[i] + np.pi/2) < 0.35:
					angle[i] = angle[i] + np.pi/2

			rotation = (angle[0] + angle[1]) / 2	#average angle correction
			rotation_deg = rotation/2/np.pi*360


	if lines is None or success is False:
		#~ answer = messagebox.askyesno("Error","Cannot locate centre, ensure cross-hairs are visible. \n\
#~ Would you like to proceed with a best guess of where the centre might be \
#~ (warning: may be innacurate)?")
		centre = (width//2, height//2)
		rotation = 0
		success = False
		cv2.circle(cropped_img, center=(width//8, height//8), radius=15, color=(0,255,0), thickness=2) #draw a circle around the centre point
		cv2.imshow("Keypoints", cropped_img)											#show centre with a line drawn
		cv2.waitKey(300)
		return centre, rotation, success

	#********************display what the code is doing:**********************
	for j in [0, i2]:
		for x1,y1,x2,y2 in lines[j]:
			cv2.line(cropped_img,(x1,y1),(x2,y2),(0,0,255),2)
		cv2.imshow("Keypoints", cropped_img)
		cv2.waitKey(1)

	cv2.circle(cropped_img, center=centre, radius=15, color=(0,255,0), thickness=2) #draw a circle around the centre point
	cv2.imshow("Keypoints", cropped_img)											#show centre with a line drawn
	cv2.waitKey(300)

	#draw the rotation:
	M = cv2.getRotationMatrix2D(centre, np.rad2deg(rotation),1)	#convert angle correction to a rotation matrix
	rot_img = cv2.warpAffine(cropped_img,M,(120,120))			#rotate the image cropped_img to show what the correction does
	cv2.imshow("Keypoints", rot_img)
	cv2.waitKey(300)
	cv2.destroyAllWindows()

	centre_uncrop = (centre[0] + topleft[0], centre[1] + topleft[1])	#update centre coordinates for un-cropped image

	return centre_uncrop, rotation_deg, success


def average_centre(n, total_frames, cap):
	'''
	Calls the find_centre function a few times and averages the result over a selection of frames.
	'''
	#throw an error if n is too large
	if total_frames-1 < n:
		print("You're trying to average {} frames to find the centre, but only have {} frames in the video. So take a longer video, or try averaging fewer frames!".format(n, total_frames))

	#Find the centre for n frames
	centre = np.zeros((n, 2))		#create a matrix to store centre values 2 wide and n down
	rotation = np.zeros(n)			#array to store n rotations to vertical
	for i in range(n):
		img = extract_next_frame(cap)
		centre[i], rotation[i], success = find_centre(img)

	centre_avg = np.mean(centre, axis=0)
	rotation_avg = np.mean(rotation)

	return centre_avg, rotation_avg, success


def adjust_coord(point , centre, rotation):
	'''
	Takes a point and transforms it by rotation and maybe scaling and maybe rolling shutter effect

	Args:
		point (x,y):
			initial point
		rotation (float):
			direction to rotate in anticlkwse +ve, in degrees
		centre (x,y):
			centre of rotation
	'''

def squared_difference_between(a, b):
	"""find the straight line difference between the points
	Args:
	x and y are both arrays(?) with 2 values (of y and x)
	"""
	d = (a[0]-b[0])**2 + (a[1]-b[1])**2
	return d

def index_absmin(a):
	'''
	find the index of the minumum value in a list
	'''
	absol = []
	for i in range(len(a)):
		absol.append(abs(a[i]))
	for i in range(len(a)):
		if min(absol) == abs(a[i]):
			return i

def setup_blob_detector():
	params = cv2.SimpleBlobDetector_Params()	#Setup SimpleBlobDetector parameters.
	params.minThreshold = 0 					#Change thresholds
	params.maxThreshold = 200
	params.thresholdStep = 10
	params.filterByArea = True 					#Filter by Area.
	params.minArea = 50
	params.maxArea = 500
	params.filterByCircularity = True 			#Filter by Circularity
	params.minCircularity = 0.5
	params.filterByConvexity = False 			#Filter by Convexity
	params.minConvexity = 0.87
	params.filterByInertia = True 				#Filter by Inertia
	params.minInertiaRatio = 0.2

	# Set up the detector with set parameters.
	detector = cv2.SimpleBlobDetector_create(params)
	return detector

def find_dots(img, detector):
	'''
	Runs blob detect on input image with settings from the 'detector' function. Returns their location
	'''
	# Read image
	img = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY) 	#convert 2 gray
	img = cv2.bitwise_not(img) 					#Invert colours so white spots are located rather than black
	keypoints = detector.detect(img)			#Detect blobs.
	return keypoints

def identify_dots(img, centre, keypoints, sq_arm1_length, sq_arm2_length):
	'''
	Use the arm lengths and centre position to estimate which dot is which based on position.
	Inputs:
		img:
			Image in which to find dots
		centre:
			Coordinates of the centre of the pendulum in the image
		keypoints:
			output of the blob detector from find_dots function
	'''
	height = img.shape[0]
	width = img.shape[1]

	points2f = cv2.KeyPoint_convert(keypoints)	#read keypoints into coordinates in the variable points2f
	if len(points2f) < 2:	#if two dots not found, return with no success
		success = False
		dot1 = [0, 0]
		dot2 = [0, 0]
		return dot1, dot2, success
	int_points2f = cv2.KeyPoint_convert(keypoints).astype(int)	#gives a ndarray of x,y coordinates converted to ints

	#find arm1 point
	sq_centre_dist = []
	sq_error1 = []
	i_blacklist = []
	for i in range(len(points2f)):
		sq_centre_dist.append(squared_difference_between(points2f[i], centre))
		sq_error1.append(sq_centre_dist[i] - sq_arm1_length)		#finds distance to arm1 diameter circle from each point
		if sq_centre_dist[i] > (height//2)**2 or sq_centre_dist[i] < (height//11)**2:	#if the dot is outside range pendulum can
			i_blacklist.append(i)										#reach, blacklist the index value (eliminates corners and centre)
	i_arm1 = index_absmin(sq_error1) 							#find dot closest to dist arm1_length away
	dot1 = points2f[i_arm1]

	#find arm2 point
	sq_arm1_dist = [100000]*len(points2f)				#initiate list of correct length that has large values.
	sq_error2 = [100000]*len(points2f)
	for i in range(len(points2f)):
		if i not in [i_arm1] + i_blacklist:
			sq_arm1_dist[i] = squared_difference_between(points2f[i], points2f[i_arm1])
			sq_error2[i] = sq_arm1_dist[i] - sq_arm2_length
		else:
			sq_arm1_dist[i] = 100000
	i_arm2 = index_absmin(sq_error2)
	dot2 = points2f[i_arm2]

	#~ #Draw ALL detected blobs as red circles. cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS ensures the size of the circle corresponds to the size of blob
	#~ img_with_keypoints = cv2.drawKeypoints(img, [keypoints[i_arm1]], np.array([]), (0,0,255), cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
	#~ img_with_keypoints = cv2.drawKeypoints(img_with_keypoints, [keypoints[i_arm2]], np.array([]), (0,255,255), cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
	#~ for i in range(len(points2f)):
		#~ if i not in [i_arm1, i_arm2]:
			#~ img_with_keypoints = cv2.drawKeypoints(img_with_keypoints, [keypoints[i]], np.array([]), (0,255,0), cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
	#~ winname = 'Blobs Detected'
	#~ #cv2.namedWindow(winname)					# Create a named window
	#~ #cv2.moveWindow(winname, 0,0)				# Move it to postition
	#~ #img_with_keypoints_S = cv2.resize(img_with_keypoints, (screen_height//2 * width//height, screen_height//2))
	#~ cv2.imshow(winname, img_with_keypoints)
	#~ cv2.waitKey(0)

	if i_arm1 in i_blacklist or i_arm2 in i_blacklist:
		success = False
	else:
		success = True

	return dot1, dot2, success

def crop_to_dot1(img, centre, a1, a2, sq_arm1_length):
	'''
	Guess where dot 1 will be using linear extrapolation, and crop image to an area around it
	'''
	box = 80 							#size of side of box to outline dot with (px)
	a_est = a2 + (a2 - a1)				#estimate of alpha
	x_est = int(round(centre[0] + np.sqrt(sq_arm1_length)*np.sin(np.deg2rad(a_est))))
	y_est = int(round(centre[1] + np.sqrt(sq_arm1_length)*np.cos(np.deg2rad(a_est))))

	img1 = img[y_est - box//2: y_est + box//2, x_est - box//2:x_est + box//2]
	topleft = [x_est - box//2, y_est - box//2]

	return img1, topleft


def crop_to_dot2(img, dot1, sq_arm2_length, b1, b2):
	'''
	Guess where dot 2 will be using linear extrapolation, and crop image to an area around it
	'''
	box = 80 #size of side of box to outline dot with (px)
	b_est = b2 + (b2-b1)
	x_est = int(round(dot1[0] + np.sqrt(sq_arm2_length)*np.sin(np.deg2rad(b_est))))
	y_est = int(round(dot1[1] + np.sqrt(sq_arm2_length)*np.cos(np.deg2rad(b_est))))
	if y_est < box//2:
		y_est = box//2
	if x_est < box//2:
		x_est = box//2

	img2 = img[y_est - box//2: y_est + box//2, x_est - box//2:x_est + box//2]
	topleft = [x_est - box//2, y_est - box//2]

	return img2, topleft

def find_angles(dot1, dot2, centre, rotation, total_frames):
	'''
	Uses the position of the arms to calculate the angles they make to vertical
	'''
	#find the angles
	a_deg = 360/2/np.pi * np.arctan2(dot1[0]-centre[0], dot1[1]-centre[1]) + rotation
	b_deg = 360/2/np.pi * np.arctan2(dot2[0]-dot1[0], dot2[1]-dot1[1]) + rotation
	return a_deg, b_deg

def stop_analysing():
	pass

def track_dots(cap, frame, detector, centre, a_deg, b_deg, dot1, dot2,
	rotation, total_frames, show_video, experiment_video_window, video_canvas, simulation_settings=[]):
	'''
	Locates dots over time (crops image down to speed up dot detection)
	Inputs:
		a_deg:
			array of alpha values up to current frame
		b_deg:
			array of beta values up to current frame
		dot1:
			array of x,y coordinates of the dot on arm1
		dot2:
			array of x,y coordinates of the dot on arm2
		rotation:
			The estimated rotation to reach true vertical
		and more!
	Outputs:
		updated a_deg, b_deg, dot1 and dot2
	'''
	img = extract_next_frame(cap)
	if np.any(img) == None:				#if the last frame has been reached (this shouldn't really happen, but the estimated number of frames by framerate and recording time might be slightly wrong.)
		return a_deg, b_deg, dot1, dot2	#just return the same arrays unaltered

	height = img.shape[0]	#size of image (px)
	width = img.shape[1]
	sq_arm1_length_def = (height*3//10)**2				#estimated length^2 of arm1 (px)
	sq_arm2_length_def = (height//6)**2					#estimated length^2 of arm2 (px)
	sq_arm1_length = sq_arm1_length_def
	sq_arm2_length = sq_arm2_length_def

	if frame in (0, 1):				#do the first two frames by searching the whole image for dots
		keypoints = find_dots(img, detector)
		dot1[frame], dot2[frame], success = identify_dots(img, centre, keypoints, sq_arm1_length, sq_arm2_length)

	else:							#do all of the other frames using extrapolation of the previous two points.
		#for dot 1
		#sq_arm1_length = squared_difference_between(centre, dot1[frame-1]) #update arm1 length dynamically
		img1, topleft1 = crop_to_dot1(img, centre, a_deg[frame-2], a_deg[frame-1], sq_arm1_length)
		keypoints = find_dots(img1, detector)
		points2f = cv2.KeyPoint_convert(keypoints)
		try:
			point1 = points2f[0]							#points 2f was a list of lists. the first list is extrcted, which is the coordinates of the best match of a blob
			dot1[frame,0] = point1[0]+topleft1[0]
			dot1[frame,1] = point1[1]+topleft1[1]

			#and for dot2
			#~ if squared_difference_between(dot1[frame-1], dot2[frame-1]) > 60: 				#this if statement to prevent value of arm length to be updated to zero
				#~ #sq_arm2_length = squared_difference_between(dot1[frame-1], dot2[frame-1])	#change length expected of arm 2 dynamically since it changes due to fisheye effect
				#~ pass
			#~ else:
				#~ sq_arm2_length = sq_arm2_length_def										#default length of arm 2 relative to the height of the image (px)

			img2, topleft2 = crop_to_dot2(img, dot1[frame], sq_arm2_length, b_deg[frame-2], b_deg[frame-1])
			keypoints = find_dots(img2, detector)
			points2f = cv2.KeyPoint_convert(keypoints)
			point2 = points2f[0]
			dot2[frame] = [point2[0]+topleft2[0], point2[1]+topleft2[1]]

			success = True # if we get this far without throwing exception, then it has been a success

		except IndexError:
			#print('Search Whole Image')
			height = img.shape[0]
			width = img.shape[1]
			sq_arm1_length = sq_arm1_length_def					#estimated length of arm1 (px)(used to be 1/4 old camera)
			sq_arm2_length = sq_arm2_length_def					#estimated length of arm2 (px)(used to be 1/8)
			keypoints = find_dots(img, detector)
			dot1[frame], dot2[frame], success = identify_dots(img, centre, keypoints, sq_arm1_length, sq_arm2_length)

	if show_video:
		#display image with the dots
		img_dotted = img
		dotone = (int(round(dot1[frame,0])), int(round(dot1[frame,1])))		#circle 'center' has to be an int value with a tuple input
		dottwo = (int(round(dot2[frame,0])), int(round(dot2[frame,1])))
		cv2.circle(img_dotted, center=dotone, radius=6, color=(0,0,255), thickness=3)	#red
		cv2.circle(img_dotted, center=dottwo, radius=6, color=(0,255,255), thickness=3)	#yellow

		#~ cv2.imshow('Blobs Detected', img_dotted)
		#~ cv2.waitKey(1)

		if frame == 0:
			height, width, no_channels = img_dotted.shape
			video_canvas.config(width=width, height=height)
		#Display the video on the 'video_canvas' canvas
		global photo #if it's not a global, it gets wiped every time the function returns, and the video flickers
		img_dotted_rgb = cv2.cvtColor(img_dotted, cv2.COLOR_BGR2RGB)
		photo = PIL.ImageTk.PhotoImage(image = PIL.Image.fromarray(img_dotted_rgb)) #convert to PhotoImage
		video_canvas.create_image(0, 0, image=photo, anchor=tk.NW)					#display PhotoImage on canvas
		experiment_video_window.update_idletasks()									#update after each frame
		experiment_video_window.lift()

	alpha, beta = find_angles(dot1[frame], dot2[frame], centre, rotation, total_frames)
	a_deg[frame] = alpha
	b_deg[frame] = beta

	if not success:
		a_deg[frame] = 0
		b_deg[frame] = 0
		dot1[frame] = [0,0]
		dot2[frame] = [0,0]
		answer = messagebox.askyesno("Error","Cannot locate both dots, continue anyway?")
		if not answer:
			cancel_function(experiment_video_window)
		else:
			pass

	return a_deg, b_deg, dot1, dot2

def cancel_function(experiment_video_window):
	'''this function is not currently used, but the infrastructure is there to have a cancel button, so the experiment
	can be cancelled mid-analysis without losing the data already collected. A cancel button would just call this function for this'''
	global cancel
	cancel = True
	experiment_video_window.destroy()
	print('cancel is now true')

def angle_vs_time(total_frames, centre, rotation, cap, fps, show_video, show_graph):
	'''
	create a list of angles a and b at respective times and plot them
	Args:
		total_frames(int):
			total no. of frames
		centre(x,y):
			position of centre point
		rotation(float):
			angle to rotate to real vertical
	Return:

	'''
	#create window on which to show the video of detected dots
	experiment_video_window = tk.Toplevel()

	#~ photo = tk.PhotoImage(file="STOP.png") # a nice stop sign, but a little unclear
	#~ cancel_button = tk.ttk.Button(experiment_window, text='Abort!',
		#~ command=lambda:cancel_function(experiment_video_window))
	#~ image = photo
	experiment_video_window.update()
	video_canvas = tk.Canvas(experiment_video_window)
	graph_frame = tk.Frame(experiment_video_window)

	#~ cancel_button.grid(row=9)
	video_canvas.grid(row=1, column=0)
	graph_frame.grid(row=1, column=1)
	#~ experiment_video_window.protocol("WM_DELETE_WINDOW", cancel_function(experiment_video_window))

	dot1 = np.zeros((total_frames, 2))
	dot2 = np.zeros((total_frames, 2))
	detector = setup_blob_detector()
	a_deg = np.zeros(total_frames)
	b_deg = np.zeros(total_frames)
	frametest = np.zeros(total_frames)
	previous_frame = -1
	if show_graph:

		fig_anim = matplotlib.figure.Figure()
		ax1_anim = fig_anim.add_subplot(2,1,1)
		ax2_anim = fig_anim.add_subplot(2,1,2)
		ax1_anim.set_xlim([0, total_frames/fps])
		ax1_anim.set_ylim([-180, 180])
		ax2_anim.set_xlim([0, total_frames/fps])
		ax2_anim.set_ylim([-180, 180])

		ln1_anim, = ax1_anim.plot([], [])
		ln2_anim, = ax2_anim.plot([], [])

		#~ # Shrink current axis by 20%
		#~ box = ax1.get_position()
		#~ ax1.set_position([box.x0, box.y0, box.width * 0.8, box.height])
		#~ box = ax2.get_position()
		#~ ax2.set_position([box.x0, box.y0, box.width * 0.8, box.height])

		#~ #set position
		#~ w = 1200
		#~ h = 300
		#~ x = 0
		#~ y = 400
		#~ fig_anim.canvas.manager.window.wm_geometry("%dx%d+%d+%d" % (w, h, x, y))

		def update(frame):
			nonlocal dot1, dot2, a_deg, b_deg, time, previous_frame, experiment_video_window, video_canvas

			if frame == previous_frame + 1:			#the funcanimation repeats frame 0 a few times before
													#getting started, so use this if to make sure the function
													#is only called once per frame; otherwise the frame analysed
													#doesn't line up with the one expected.
				a_deg, b_deg, dot1, dot2 = track_dots(cap, frame, detector, centre, a_deg, b_deg,
										dot1, dot2, rotation, total_frames, show_video, experiment_video_window, video_canvas)
			previous_frame = frame

			x = range(frame + 1)
			time = [i/fps for i in x]		#convert to time
			ln1_anim.set_data(time, a_deg[0:frame+1])
			ln2_anim.set_data(time, b_deg[0:frame+1])

			if frame == total_frames - 1:
				nonlocal pause_here
				pause_here = 0

			experiment_video_window.update()
			global cancel
			if cancel == True:
				cancel = False
				ani.event_source.stop()
				experiment_video_window.destroy()
				#~ cv2.destroyAllWindows()

			return ln1_anim, ln2_anim

		graph_canvas = FigureCanvasTkAgg(fig_anim, master=graph_frame)#plot the graph on a canvas within the graph_frame
		graph_canvas.get_tk_widget().pack()

		pause_here = 1

		ani = anim.FuncAnimation(fig_anim, update, frames=total_frames, interval=1, blit=True, repeat=False)

		experiment_video_window.update()
		while pause_here:
			experiment_video_window.update()
		experiment_video_window.destroy()

	else:
		for frame in range(total_frames):
			a_deg, b_deg, dot1, dot2 = track_dots(cap, frame, detector, centre, a_deg, b_deg,
				dot1, dot2, rotation, total_frames, show_video, experiment_video_window, video_canvas)

			experiment_video_window.update()
			global cancel
			if cancel == True:
				cancel = False
				break

			frametest[frame] = 6

	x = range(len(a_deg))
	time = [i/fps for i in x]		#convert to time

	#~ cv2.destroyAllWindows()
	experiment_video_window.destroy()

	return time, a_deg, b_deg

def extract_frame(folder, frame):
	'''
	load a frame to the variable img from the specified location
	Args:
		folder (str):
			folder where the frames are stored
		frame (int):
			the number frame to be extracted.
	'''
	file_path = os.path.join(folder,'frame{}.jpg'.format(frame))
	img = cv2.imread(file_path, cv2.IMREAD_COLOR)
	return img

def record_video_and_locate_centre(video_length=3, fps=90, width=480, height=480, orienting_frames=2, show_video=True, show_graph=False):
	'''Takes a video of double pendulum action, and produces the outputs asked for.
	Inputs:
		video_length:
			length of video (s)
		fps:
			frames per second for video
		width:
			width of video (px)
		height:
			height of video (px)
		orienting_frames:
			number of video frames used to find the pendulum centre using the cross-hairs
		show_video:
			whether to show each frame as it is analysed
		show_graph:
			whether to show animated graph as each frame is analysed
	Outputs:
		t, a, b:
			list of numbers for time, alpha and beta'''

	total_frames = video_length * fps						#take a video
	record_video(video_length, width, height, fps)

	cap = init_frame_extraction()							#initiate frame extraction
	img = extract_next_frame(cap)
	centre, rotation, success = average_centre(orienting_frames, total_frames, cap)	#find the centre of a frame and orient

	return total_frames, centre, rotation, success

def track_dots_and_plot(total_frames, centre, rotation, video_length=3, fps=90, width=480,
						height=480, orienting_frames=2, show_video=True, show_graph=False, view_fourier=True):

	cap = init_frame_extraction()	#call this again, so the blobs are found in the first few frames
	t, a, b = angle_vs_time(total_frames, centre, rotation, cap, fps, show_video, show_graph)	#produce a list of times vs angles a and b
	if max(a) < 45 and max(b) < 90:
		modeshape, resonance = small_angles(t, a, b, fps, view_fourier)
	else:
		modeshape, resonance = None, None
	return t, a, b, modeshape, resonance

def find_start_points(t, a, b, tref=None, aref=None, bref=None, fps=90):
	'''
	Detect when the graph starts to change, and crop the data to that point.
	'''
	try:
		length = min(len(t), len(a), len(b))	# first ensure that the lists are of the same length
		t = t[:length]							# of course, they should be
		a = a[:length]							# but I don't trust the previous code
		b = b[:length]

		#***************work in progress: doing a best fit between lines to position them on the graph*******************
		#~ #do it by closest match if data to match it to is given
		#~ sumlist = []
		#~ search_area = 90 #the following code searches an area of plus/minus 'search_area' many data points for the best fit
		#~ if tref is not None and aref is not None and bref is not None:
			#~ for shift in range(-search_area, search_area):
				#~ asum, bsum = 0, 0
				#~ for i in range(120):
					#~ asum += abs(aref[i-shift] - a[i])**2
					#~ bsum += abs(bref[i-shift] - b[i])**2
				#~ sumlist.append(asum+bsum)
			#~ print('the following step is the real problem')
			#~ bestshift = min(range(len(sumlist)), key=sumlist.__getitem__) - search_area
			#~ print('the following step is the problem?')
			#~ print('bestshift is {}'.format(bestshift))
			#~ print('t[bestshift] is {}'.format(t[bestshift]))
			#~ t_mod = np.fromiter( [j + bestshift/fps for j in t], float)
			#~ print('no, it wasnt')
			#~ return t_mod, a, b

		#otherwise do it by change in angle
		#~ else:
		for i in range(len(t)):
			b_change = abs(b[0] - b[i])
			a_change = abs(a[0] - a[i])
			if a_change > 20 or b_change > 30:
				k = i-5
				t_mod = np.fromiter( [j-t[k] for j in t], float)
				return t_mod, a, b
		return t, a, b

	except Exception as e:
		print (e)
		print('Couldn\'t find start of angle data')
		return 0,0,0

def small_angles(t, a, b, fps=90, view_graph=True):

	#take fft of alpha and beta
	a_fourier = abs(np.fft.rfft(a))
	b_fourier = abs(np.fft.rfft(b))
	N = len(a_fourier)
	freq = [ i/N * fps /2 for i in range(N) ]
	df = fps/N

	a, b, c = [0,0], [0,0], [0,0]

	for n, y in enumerate([a_fourier, b_fourier]):
		i = np.argmax(y)
		a[n] = ( y[i+1] - 2*y[i] + y[i-1] ) / ( 2* df*df )
		b[n] = ( y[i+1] - y[i-1] ) / ( 2*df ) - 2*a[n]*freq[i]
		c[n] = y[i] - a[n]*freq[i]**2 - b[n]*freq[i]
	print ('a: {}\nb: {}\nc: {}\ni: {}'.format(a,b,c,i))

	fpeak, ypeak = [0,0], [0,0]
	for i in [0,1]:
		fpeak[i] = -b[i]/(2*a[i])
		ypeak[i] = a[i] * fpeak[i]**2 + b[i] * fpeak[i] + c[i]

	print('fpeak is {}'.format(fpeak))
	print('ypeak is {}'.format(ypeak))

	if view_graph:
		#setup graph for fourier
		fig = matplotlib.figure.Figure()
		ax1 = fig.add_subplot(2,1,1)
		ax2 = fig.add_subplot(2,1,2)
		#~ ax1.set_ylim([-180,180])						#set y limits
		#~ ax2.set_ylim([-180,180])
		#~ ax1.set_xlim(left=0, auto=True)
		#~ ax1.yaxis.set_ticks(np.arange(-180, 181, 90))	#format x axis labels.
		#~ ax2.yaxis.set_ticks(np.arange(-180, 181, 90))
		ax1.grid(linestyle='--', which='both')			#format gridlines
		ax2.grid(linestyle='--', which='both')
		ax1.set_ylabel('\u03b1 response')				#axis labels: 03b1 is alpha, 03b2 is beta, 00b0 is degree
		ax2.set_ylabel('\u03b2 response')
		ax2.set_xlabel('Frequency [Hz]')
		ax1.grid(True)									#remove the numbers from the x axis of the top plot for neatness
		ax1.xaxis.set_ticklabels([])
		ln1, = ax1.plot(freq, a_fourier)#, label=legend_a)
		ln2, = ax2.plot(freq, b_fourier)#, label=legend_b)

		ax1.plot(fpeak[0], ypeak[0], 'rx')#, label=legend_a)
		ax2.plot(fpeak[1], ypeak[1], 'rx')#, label=legend_b)

		fig.tight_layout()

		#display graph
		root_small_angle = tk.Toplevel()
		root_small_angle.title('Fourier Transform of alpha and beta')
		canvas = FigureCanvasTkAgg(fig, master=root_small_angle)
		canvas.get_tk_widget().pack(side='top', fill='both', expand=1)

		toolbar = NavigationToolbar2Tk(canvas, root_small_angle)
		toolbar.update()
		canvas._tkcanvas.pack(side='top', fill='both', expand=1)

		canvas.draw()

	#modeshape
	modeshape = ypeak[0]/ypeak[1]
	resonance = (fpeak[0]+fpeak[1])/2

	return modeshape, resonance


def main():
	t,c,r = record_video_and_locate_centre()
	track_dots_and_plot(t,c,r)


if __name__ == '__main__':
    main()
