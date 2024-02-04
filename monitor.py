#!/usr/bin/env python

import json
import logging
import RPi.GPIO as GPIO
import smbus
import struct
import sys
from time import sleep

BATTERY_FILE_PATH = 'battery.json'
CHARGING_STATUS_PORT = 6
I2C_ADDR = 0x36

class BatteryMonitor:
    def __init__(self, bus_number=1, address=0x36):
        self.bus = smbus.SMBus(bus_number)
        self.address = address

    def readVoltage(self):
        try:
            read = self.bus.read_word_data(self.address, 2)
            swapped = struct.unpack("<H", struct.pack(">H", read))[0]
            return swapped * 1.25 / 1000 / 16
        except Exception as e:
            logging.error("Error reading voltage: %s", e)
            return None

    def readCapacity(self):
        try:
            read = self.bus.read_word_data(self.address, 4)
            swapped = struct.unpack("<H", struct.pack(">H", read))[0]
            capacity = min(swapped / 256, 99)
            return int(capacity)
        except Exception as e:
            logging.error("Error reading capacity: %s", e)
            return None

# Function to prepare capacity reading for display
def prepare_readCapacity(battery_monitor):
    capacity = battery_monitor.readCapacity()
    capacity_left_digit = capacity // 100
    capacity_middle_digit = capacity // 10
    capacity_right_digit = capacity % 10
    return capacity_left_digit, capacity_middle_digit, capacity_right_digit

# Function to prepare voltage reading for display
def prepare_readVoltage(battery_monitor):
    voltage = battery_monitor.readVoltage()
    if voltage > 3.65:
        return 'six'
    elif 3.60 < voltage <= 3.65:
        return 'five'
    elif 3.55 < voltage <= 3.60:
        return 'four'
    elif 3.50 < voltage <= 3.55:
        return 'three'
    elif 3.45 < voltage <= 3.50:
        return 'two'
    elif 3.40 < voltage <= 3.45:
        return 'one'
    elif voltage <= 3.40:
        return 'off'

# Function to send status to JSON file
def send_status(capacity_left_digit, capacity_middle_digit, capacity_right_digit, voltage_bar):
    data = {
        'left': capacity_left_digit,
        'middle': capacity_middle_digit,
        'right': capacity_right_digit,
        'volts': voltage_bar
    }
    with open(BATTERY_FILE_PATH, 'w') as f:
        json.dump(data, f)

##########

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(CHARGING_STATUS_PORT, GPIO.IN)

    battery_monitor = BatteryMonitor()

    try:
        while True:
            try:
                capacity_left_digit, capacity_middle_digit, capacity_right_digit = prepare_readCapacity(battery_monitor)
                voltage_bar = prepare_readVoltage(battery_monitor)
                send_status(capacity_left_digit, capacity_middle_digit, capacity_right_digit, voltage_bar)
                sleep(5)
            except Exception as e:
                logging.error("An error occurred in the main loop: %s", e)
                sleep(1)
    finally:
        GPIO.cleanup()
        logging.info("GPIO cleanup complete.")

if __name__ == '__main__':
    main()