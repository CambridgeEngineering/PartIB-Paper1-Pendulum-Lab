# Installation Instructions

## Install Raspbian

Follow the instructions at

<https://www.raspberrypi.com/software/>

When the installation process prompts you to install operating system updates,
skip that step, because the Raspberry Pi won't be able to access a time server
yet, and the update will fail.

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

## Update the operating system

Give the commands

    sudo apt update
    sudo apt full-upgrade

When the updates have installed, reboot the Raspberry Pi for good measure.

## Enable the legacy camera interface

From a command window, give the command

    sudo raspi-config

choose the "Interface Options" screen, and then enable "Legacy Camera".

## Install the software

Create a clone of the GitHub repository and run the installer script.

    git clone https://github.com/CambridgeEngineering/PartIB-Paper1-Pendulum-Lab.git
    cd PartIB-Paper1-Pendulum-Lab/src
    sudo make install

Reboot the Raspberry Pi again.

## Configure email

Create a file

/home/pi/.DoublePendulum.email

which contains a gmail username and password to be used to send experiment results by email, for example,

    johnsmith
    greeneggsandspam

(but not those particular values, obviously!)
