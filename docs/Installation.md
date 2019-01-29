# Installation Instructions

## Install Raspbian

Follow the instructions at

<https://projects.raspberrypi.org/en/projects/noobs-install>

## Use the CUED time server

Give the command

    sudo nano /etc/systemd/timesyncd.conf

under `[Time]` add a line

    Servers=ntp1.eng.cam.ac.uk

and type ctrl+o, ctrl+x to save the file and leave the *nano* editor. Type

    sudo systemctl daemon-reload
    sudo systemctl restart systemd-timesyncd
    date

and the correct date and time should be shown.

## Install OpenCV

At the time of writing there's no pre-packaged installer for Raspberry Pi, so follow the instructions at

<https://www.life2coding.com/install-opencv-3-4-0-python-3-raspberry-pi-3/>

to build and install *OpenCV* from source.

There's plenty of space on the SD card, so you can start from step 3.
In Step 9, you *do* need to do the rename step.

## Enable the Camera

Menu => Preferences => Raspberry pi configuration

Then, in the Interfaces tab, set Camera to 'enabled'

## Install the software

Create a clone of the GitHub repository and run the installer script.

    git clone https://github.com/CambridgeEngineering/PartIB-Paper1-Pendulum-Lab.git
    cd PartIB-Paper1-Pendulum-Lab/src
    sudo make install

and reboot.

## Configure email

Create a file

/home/pi/.DoublePendulum.email

which contains a gmail username and password to be used to send experiment results by email, for example,

    johnsmith
    greeneggsandspam

(but not those particular values, obviously!)
