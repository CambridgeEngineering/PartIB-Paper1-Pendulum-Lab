install:
	apt-get install python3-matplotlib -y
	apt-get install python3-scipy -y
	apt-get install python3-pil -y
	apt-get install python3-pil.imagetk -y

	install --backup=off --owner=pi DoublePendulumGUI.py        /home/pi/
	install --backup=off --owner=pi DoublePendulum_PivotMass.py /home/pi/
	install --backup=off --owner=pi DoublePendulumProgram.py    /home/pi/
	install --backup=off --owner=pi info_icon.png               /home/pi/
	install --backup=off --owner=pi pendulum_icon.png           /home/pi/
	install --backup=off --owner=pi preview_overlay.png         /home/pi/
	install --backup=off --owner=pi DoublePendulumDiagram.gif   /home/pi/

	install --backup=off --owner=pi DoublePendulum.desktop      /home/pi/Desktop

	install --backup=off --mode=644 pendulumGUI.service         /lib/systemd/system/

	systemctl daemon-reload
	systemctl enable pendulumGUI.service
