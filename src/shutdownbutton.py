import time
import os
import argparse
import RPi.GPIO as GPIO

# Read the command line.

ap = argparse.ArgumentParser('Shutdown RPi on detecting button press')

ap.add_argument(
    '--pin', type=int, default=3,
    help='GPIO pin to monitor [3]'
)
ap.add_argument(
    '--duration', type=float, default=3.0,
    help='Required press duration [3.0]'
)

args = ap.parse_args()

pin = args.pin
tmo = int(round(args.duration) * 1000)

fmt = 'To shutdown the RPi, pull GPIO{} to ground for at least {} ms'
print(fmt.format(pin, tmo), flush=True)

# Setup the GPIO pin.

GPIO.setmode(GPIO.BCM)

if pin in (2, 3):   # Note that GPIO 2 and 3 already have fixed pullups.
    GPIO.setup(pin, GPIO.IN)
else:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Loop handling button presses.

while True:

    # Wait for pin to be pulled low by the pushbutton, allowing for switch
    # bounce by checking that it is still low 10ms later.

    while GPIO.input(pin):
        GPIO.wait_for_edge(pin, GPIO.FALLING)
        time.sleep(0.010)

    # Wait for the pin to go high again. If this is sooner than the required
    # duration, then ignore the press and loop back for the next one. If we've
    # exceeded the required duration then we're done.

    edge = GPIO.wait_for_edge(pin, GPIO.RISING, timeout=tmo)
    if edge is None:
        break

# A long duration button press has been detected: shut the machine down.

print('Closing system down', flush=True)
os.system('sudo poweroff')
