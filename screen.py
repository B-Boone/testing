import RPi.GPIO as GPIO
from threading import Thread, Event
from time import sleep
import psutil
import json
import os

class LEDDisplay:
    REFRESH_RATE = 0.0001
    BATTERY_FILE_PATH = 'battery.json'

    def __init__(self):
        self.pins = {
            'Pin1': 17, 'Pin2': 27, 'Pin3': 22, 'Pin4': 23, 'Pin5': 24, 'Pin6': 25, 'Pin7': 13, 'Pin8': 16,
        }
        self.setup_gpio()

        self.voltage_bar = ['off']
        self.capacity_left_digit = [0]
        self.capacity_middle_digit = [0]
        self.capacity_right_digit = [0]
        self.misc_lights = ['off']
        self.usage_arrow = ['off']
        self.temp_left_digit = [0]
        self.temp_middle_digit = [0]
        self.temp_right_digit = [0]
        self.ram_bar = ['off']
        
        self.stop_event = Event()

        # Define segment control mappings for a multiplexed display
        self.segment_mappings = {
            'voltage_bar': {
                'off': [],
                'one': [(self.pins['Pin1'], self.pins['Pin8'])],
                'two': [(self.pins['Pin2'], self.pins['Pin8']), (self.pins['Pin1'], self.pins['Pin8'])],
                'three': [(self.pins['Pin3'], self.pins['Pin8']), (self.pins['Pin2'], self.pins['Pin8']), (self.pins['Pin1'], self.pins['Pin8'])],
                'four': [(self.pins['Pin4'], self.pins['Pin8']), (self.pins['Pin3'], self.pins['Pin8']), (self.pins['Pin2'], self.pins['Pin8']), (self.pins['Pin1'], self.pins['Pin8'])],
                'five': [(self.pins['Pin7'], self.pins['Pin8']), (self.pins['Pin4'], self.pins['Pin8']), (self.pins['Pin3'], self.pins['Pin8']), (self.pins['Pin2'], self.pins['Pin8']), (self.pins['Pin1'], self.pins['Pin8'])],
                'six': [(self.pins['Pin5'], self.pins['Pin8']), (self.pins['Pin7'], self.pins['Pin8']), (self.pins['Pin4'], self.pins['Pin8']), (self.pins['Pin3'], self.pins['Pin8']), (self.pins['Pin2'], self.pins['Pin8']), (self.pins['Pin1'], self.pins['Pin8'])]
            },
            'capacity_left_digit': {
                0: [],
                1: [(self.pins['Pin2'], self.pins['Pin7']), (self.pins['Pin3'], self.pins['Pin7'])]
            },
            'capacity_middle_digit': {
                0: [(self.pins['Pin2'], self.pins['Pin1']), (self.pins['Pin3'], self.pins['Pin1']), (self.pins['Pin4'], self.pins['Pin1']), (self.pins['Pin8'], self.pins['Pin1']), (self.pins['Pin7'], self.pins['Pin1']), (self.pins['Pin5'], self.pins['Pin1'])],
                1: [(self.pins['Pin3'], self.pins['Pin1']), (self.pins['Pin4'], self.pins['Pin1'])],
                2: [(self.pins['Pin2'], self.pins['Pin1']), (self.pins['Pin3'], self.pins['Pin1']), (self.pins['Pin8'], self.pins['Pin1']), (self.pins['Pin7'], self.pins['Pin1']), (self.pins['Pin6'], self.pins['Pin1'])],
                3: [(self.pins['Pin2'], self.pins['Pin1']), (self.pins['Pin3'], self.pins['Pin1']), (self.pins['Pin4'], self.pins['Pin1']), (self.pins['Pin8'], self.pins['Pin1']), (self.pins['Pin6'], self.pins['Pin1'])],
                4: [(self.pins['Pin3'], self.pins['Pin1']), (self.pins['Pin4'], self.pins['Pin1']), (self.pins['Pin5'], self.pins['Pin1']), (self.pins['Pin6'], self.pins['Pin1'])],
                5: [(self.pins['Pin2'], self.pins['Pin1']), (self.pins['Pin4'], self.pins['Pin1']), (self.pins['Pin8'], self.pins['Pin1']), (self.pins['Pin7'], self.pins['Pin1']), (self.pins['Pin6'], self.pins['Pin1'])],
                6: [(self.pins['Pin2'], self.pins['Pin1']), (self.pins['Pin4'], self.pins['Pin1']), (self.pins['Pin8'], self.pins['Pin1']), (self.pins['Pin7'], self.pins['Pin1']), (self.pins['Pin5'], self.pins['Pin1']), (self.pins['Pin6'], self.pins['Pin1'])],
                7: [(self.pins['Pin2'], self.pins['Pin1']), (self.pins['Pin3'], self.pins['Pin1']), (self.pins['Pin4'], self.pins['Pin1'])],
                8: [(self.pins['Pin2'], self.pins['Pin1']), (self.pins['Pin3'], self.pins['Pin1']), (self.pins['Pin4'], self.pins['Pin1']), (self.pins['Pin8'], self.pins['Pin1']), (self.pins['Pin7'], self.pins['Pin1']), (self.pins['Pin5'], self.pins['Pin1']), (self.pins['Pin6'], self.pins['Pin1'])],
                9: [(self.pins['Pin2'], self.pins['Pin1']), (self.pins['Pin3'], self.pins['Pin1']), (self.pins['Pin4'], self.pins['Pin1']), (self.pins['Pin8'], self.pins['Pin1']), (self.pins['Pin5'], self.pins['Pin1']), (self.pins['Pin6'], self.pins['Pin1'])]
            },
            'capacity_right_digit': {
                0: [(self.pins['Pin1'], self.pins['Pin2']), (self.pins['Pin3'], self.pins['Pin2']), (self.pins['Pin4'], self.pins['Pin2']), (self.pins['Pin8'], self.pins['Pin2']), (self.pins['Pin7'], self.pins['Pin1']), (self.pins['Pin5'], self.pins['Pin4'])],
                1: [(self.pins['Pin3'], self.pins['Pin2']), (self.pins['Pin4'], self.pins['Pin2'])],
                2: [(self.pins['Pin1'], self.pins['Pin2']), (self.pins['Pin3'], self.pins['Pin2']), (self.pins['Pin8'], self.pins['Pin2']), (self.pins['Pin7'], self.pins['Pin2']), (self.pins['Pin6'], self.pins['Pin2'])],
                3: [(self.pins['Pin1'], self.pins['Pin2']), (self.pins['Pin3'], self.pins['Pin2']), (self.pins['Pin4'], self.pins['Pin2']), (self.pins['Pin8'], self.pins['Pin2']), (self.pins['Pin6'], self.pins['Pin2'])],
                4: [(self.pins['Pin3'], self.pins['Pin2']), (self.pins['Pin4'], self.pins['Pin2']), (self.pins['Pin5'], self.pins['Pin2']), (self.pins['Pin6'], self.pins['Pin2'])],
                5: [(self.pins['Pin1'], self.pins['Pin2']), (self.pins['Pin4'], self.pins['Pin2']), (self.pins['Pin8'], self.pins['Pin2']), (self.pins['Pin5'], self.pins['Pin2']), (self.pins['Pin6'], self.pins['Pin2'])],
                6: [(self.pins['Pin1'], self.pins['Pin2']), (self.pins['Pin4'], self.pins['Pin2']), (self.pins['Pin8'], self.pins['Pin2']), (self.pins['Pin7'], self.pins['Pin2']), (self.pins['Pin5'], self.pins['Pin2']), (self.pins['Pin6'], self.pins['Pin2'])],
                7: [(self.pins['Pin1'], self.pins['Pin2']), (self.pins['Pin3'], self.pins['Pin2']), (self.pins['Pin4'], self.pins['Pin2'])],
                8: [(self.pins['Pin1'], self.pins['Pin2']), (self.pins['Pin3'], self.pins['Pin2']), (self.pins['Pin4'], self.pins['Pin2']), (self.pins['Pin8'], self.pins['Pin2']), (self.pins['Pin7'], self.pins['Pin2']), (self.pins['Pin5'], self.pins['Pin2']), (self.pins['Pin6'], self.pins['Pin2'])],
                9: [(self.pins['Pin1'], self.pins['Pin2']), (self.pins['Pin3'], self.pins['Pin2']), (self.pins['Pin4'], self.pins['Pin2']), (self.pins['Pin8'], self.pins['Pin2']), (self.pins['Pin5'], self.pins['Pin2']), (self.pins['Pin6'], self.pins['Pin2'])]
            },
            'misc_lights': {
                'on': [(self.pins['Pin6'], self.pins['Pin8']), (self.pins['Pin1'], self.pins['Pin7']), (self.pins['Pin1'], self.pins['Pin5']), (self.pins['Pin8'], self.pins['Pin5']), (self.pins['Pin2'], self.pins['Pin5']), (self.pins['Pin7'], self.pins['Pin5']), (self.pins['Pin5'], self.pins['Pin6'])],
                'off': []
            },
            'usage_arrow': {
                'turbo': [(self.pins['Pin3'], self.pins['Pin5'])],
                'norm': [(self.pins['Pin4'], self.pins['Pin5'])],
                'off': []
            },
            'temp_left_digit': {
                0: [],
                1: [(self.pins['Pin5'], self.pins['Pin7']), (self.pins['Pin8'], self.pins['Pin7'])]
            },
            'temp_middle_digit': {
                0: [(self.pins['Pin1'], self.pins['Pin3']), (self.pins['Pin2'], self.pins['Pin3']), (self.pins['Pin4'], self.pins['Pin3']), (self.pins['Pin8'], self.pins['Pin3']), (self.pins['Pin7'], self.pins['Pin3']), (self.pins['Pin5'], self.pins['Pin3'])],
                1: [(self.pins['Pin2'], self.pins['Pin3']), (self.pins['Pin4'], self.pins['Pin3'])],
                2: [(self.pins['Pin1'], self.pins['Pin3']), (self.pins['Pin2'], self.pins['Pin3']), (self.pins['Pin8'], self.pins['Pin3']), (self.pins['Pin7'], self.pins['Pin3']), (self.pins['Pin6'], self.pins['Pin3'])],
                3: [(self.pins['Pin1'], self.pins['Pin3']), (self.pins['Pin2'], self.pins['Pin3']), (self.pins['Pin4'], self.pins['Pin3']), (self.pins['Pin8'], self.pins['Pin3']), (self.pins['Pin6'], self.pins['Pin3'])],
                4: [(self.pins['Pin2'], self.pins['Pin3']), (self.pins['Pin4'], self.pins['Pin3']), (self.pins['Pin5'], self.pins['Pin3']), (self.pins['Pin6'], self.pins['Pin3'])],
                5: [(self.pins['Pin1'], self.pins['Pin3']), (self.pins['Pin4'], self.pins['Pin3']), (self.pins['Pin8'], self.pins['Pin3']), (self.pins['Pin7'], self.pins['Pin3']), (self.pins['Pin6'], self.pins['Pin3'])],
                6: [(self.pins['Pin1'], self.pins['Pin3']), (self.pins['Pin4'], self.pins['Pin3']), (self.pins['Pin8'], self.pins['Pin3']), (self.pins['Pin7'], self.pins['Pin3']), (self.pins['Pin5'], self.pins['Pin3']), (self.pins['Pin6'], self.pins['Pin3'])],
                7: [(self.pins['Pin1'], self.pins['Pin3']), (self.pins['Pin2'], self.pins['Pin3']), (self.pins['Pin4'], self.pins['Pin3'])],
                8: [(self.pins['Pin1'], self.pins['Pin3']), (self.pins['Pin2'], self.pins['Pin3']), (self.pins['Pin4'], self.pins['Pin3']), (self.pins['Pin8'], self.pins['Pin3']), (self.pins['Pin7'], self.pins['Pin3']), (self.pins['Pin5'], self.pins['Pin3']), (self.pins['Pin6'], self.pins['Pin3'])],
                9: [(self.pins['Pin1'], self.pins['Pin3']), (self.pins['Pin2'], self.pins['Pin3']), (self.pins['Pin4'], self.pins['Pin3']), (self.pins['Pin8'], self.pins['Pin3']), (self.pins['Pin5'], self.pins['Pin3']), (self.pins['Pin6'], self.pins['Pin3'])]
            },
            'temp_right_digit': {
                0: [(self.pins['Pin1'], self.pins['Pin4']), (self.pins['Pin2'], self.pins['Pin4']), (self.pins['Pin3'], self.pins['Pin4']), (self.pins['Pin8'], self.pins['Pin4']), (self.pins['Pin7'], self.pins['Pin4']), (self.pins['Pin5'], self.pins['Pin4'])],
                1: [(self.pins['Pin2'], self.pins['Pin4']), (self.pins['Pin3'], self.pins['Pin4'])],
                2: [(self.pins['Pin1'], self.pins['Pin4']), (self.pins['Pin2'], self.pins['Pin4']), (self.pins['Pin8'], self.pins['Pin4']), (self.pins['Pin7'], self.pins['Pin4']), (self.pins['Pin6'], self.pins['Pin4'])],
                3: [(self.pins['Pin1'], self.pins['Pin4']), (self.pins['Pin2'], self.pins['Pin4']), (self.pins['Pin3'], self.pins['Pin4']), (self.pins['Pin8'], self.pins['Pin4']), (self.pins['Pin6'], self.pins['Pin4'])],
                4: [(self.pins['Pin2'], self.pins['Pin4']), (self.pins['Pin3'], self.pins['Pin4']), (self.pins['Pin5'], self.pins['Pin4']), (self.pins['Pin6'], self.pins['Pin4'])],
                5: [(self.pins['Pin1'], self.pins['Pin4']), (self.pins['Pin3'], self.pins['Pin4']), (self.pins['Pin8'], self.pins['Pin4']), (self.pins['Pin5'], self.pins['Pin4']), (self.pins['Pin6'], self.pins['Pin4'])],
                6: [(self.pins['Pin1'], self.pins['Pin4']), (self.pins['Pin3'], self.pins['Pin4']), (self.pins['Pin8'], self.pins['Pin4']), (self.pins['Pin7'], self.pins['Pin4']), (self.pins['Pin5'], self.pins['Pin4']), (self.pins['Pin6'], self.pins['Pin4'])],
                7: [(self.pins['Pin1'], self.pins['Pin4']), (self.pins['Pin2'], self.pins['Pin4']), (self.pins['Pin3'], self.pins['Pin4'])],
                8: [(self.pins['Pin1'], self.pins['Pin4']), (self.pins['Pin2'], self.pins['Pin4']), (self.pins['Pin3'], self.pins['Pin4']), (self.pins['Pin8'], self.pins['Pin4']), (self.pins['Pin7'], self.pins['Pin4']), (self.pins['Pin5'], self.pins['Pin4']), (self.pins['Pin6'], self.pins['Pin4'])],
                9: [(self.pins['Pin1'], self.pins['Pin4']), (self.pins['Pin2'], self.pins['Pin4']), (self.pins['Pin3'], self.pins['Pin4']), (self.pins['Pin8'], self.pins['Pin4']), (self.pins['Pin5'], self.pins['Pin4']), (self.pins['Pin6'], self.pins['Pin4'])]
            },
            'ram_bar': {
                'off': [],
                'one': [(self.pins['Pin1'], self.pins['Pin6'])],
                'two': [(self.pins['Pin2'], self.pins['Pin6']), (self.pins['Pin1'], self.pins['Pin6'])],
                'three': [(self.pins['Pin3'], self.pins['Pin6']), (self.pins['Pin2'], self.pins['Pin6']), (self.pins['Pin1'], self.pins['Pin6'])],
                'four': [(self.pins['Pin4'], self.pins['Pin6']), (self.pins['Pin3'], self.pins['Pin6']), (self.pins['Pin2'], self.pins['Pin6']), (self.pins['Pin1'], self.pins['Pin6'])],
                'five': [(self.pins['Pin8'], self.pins['Pin6']), (self.pins['Pin4'], self.pins['Pin6']), (self.pins['Pin3'], self.pins['Pin6']), (self.pins['Pin2'], self.pins['Pin6']), (self.pins['Pin1'], self.pins['Pin6'])],
                'six': [(self.pins['Pin7'], self.pins['Pin6']), (self.pins['Pin8'], self.pins['Pin6']), (self.pins['Pin4'], self.pins['Pin6']), (self.pins['Pin3'], self.pins['Pin6']), (self.pins['Pin2'], self.pins['Pin6']), (self.pins['Pin1'], self.pins['Pin6'])]
            }
        }

    def setup_gpio(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        for pin in self.pins.values():
            GPIO.setup(pin, GPIO.IN)

    def set_segment(self, pin_high, pin_low):
        for pin in self.pins.values():
            GPIO.setup(pin, GPIO.IN)
        GPIO.setup(pin_high, GPIO.OUT)
        GPIO.setup(pin_low, GPIO.OUT)
        GPIO.output(pin_high, GPIO.HIGH)
        GPIO.output(pin_low, GPIO.LOW)

    def clear_segments(self):
        for pin in self.pins.values():
            GPIO.setup(pin, GPIO.IN)

    def display_segment(self, segments):
        for pin_high, pin_low in segments:
            self.set_segment(pin_high, pin_low)
            sleep(self.REFRESH_RATE)

    def update_display(self):
        while not self.stop_event.is_set():
            self.clear_segments()
            self.display_segment(self.segment_mappings['voltage_bar'][self.voltage_bar[0]])
            self.display_segment(self.segment_mappings['capacity_left_digit'][self.capacity_left_digit[0]])
            self.display_segment(self.segment_mappings['capacity_middle_digit'][self.capacity_middle_digit[0]])
            self.display_segment(self.segment_mappings['capacity_right_digit'][self.capacity_right_digit[0]])
            self.display_segment(self.segment_mappings['misc_lights'][self.misc_lights[0]])
            self.display_segment(self.segment_mappings['usage_arrow'][self.usage_arrow[0]])
            self.display_segment(self.segment_mappings['temp_left_digit'][self.temp_left_digit[0]])
            self.display_segment(self.segment_mappings['temp_middle_digit'][self.temp_middle_digit[0]])
            self.display_segment(self.segment_mappings['temp_right_digit'][self.temp_right_digit[0]])
            self.display_segment(self.segment_mappings['ram_bar'][self.ram_bar[0]])
            sleep(self.REFRESH_RATE)

    def get_ram_usage(self):
        # Run the 'free' command and capture its output
        output = os.popen('free -m').readlines()
        
        # Extract the memory line, split it into components
        mem_components = output[1].split()

        # Get total and used memory in megabytes
        total_mem = int(mem_components[1])
        used_mem = int(mem_components[2])

        # Calculate the percentage of used memory
        percentage_used = (used_mem / total_mem) * 100

        # Determine the RAM indicator based on the percentage used
        if percentage_used >= 80:
            return 'six'
        elif percentage_used >= 60:
            return 'five'
        elif percentage_used >= 40:
            return 'four'
        elif percentage_used >= 20:
            return 'three'
        elif percentage_used >= 10:
            return 'two'
        else:
            return 'one'

    def read_data(self):
        while not self.stop_event.is_set():
            try:
                self.misc_lights[0] = 'on'
                with open("/sys/class/thermal/thermal_zone0/temp", "r") as file:
                    temp = int(file.read()) / 1000  # Convert to Celsius
                # Assuming you want to display the temperature in three digits
                self.temp_left_digit[0] = int(temp) // 100 # Hundreds place
                self.temp_middle_digit[0] = int(temp) // 10  # Tens place
                self.temp_right_digit[0] = int(temp) % 10  # Ones place

                cpu_usage = psutil.cpu_percent(interval=1)  # Get CPU usage percentage
                # Display CPU usage on LED segments
                # Determine percent symbol status based on CPU usage
                if cpu_usage == 100:
                    self.usage_arrow[0] = 'turbo'  # Set to on when CPU usage is 100%
                else:
                    self.usage_arrow[0] = 'norm'

                with open(self.BATTERY_FILE_PATH, 'r') as file:
                    data = json.load(file)
                self.capacity_left_digit[0] = data.get('left', 0)
                self.capacity_middle_digit[0] = data.get('middle', 0)
                self.capacity_right_digit[0] = data.get('right', 0)
                self.voltage_bar[0] = data.get('volts', 'off')

                # Call the get_ram_usage function to update RAM indicator
                self.ram_bar[0] = self.get_ram_usage()

            except Exception as e:
                print(f"Error: {e}")
            sleep(1)

    def start(self):
        Thread(target=self.read_data, daemon=True).start()
        Thread(target=self.update_display, daemon=True).start()

    def stop(self):
        self.stop_event.set()
        self.clear_segments()
        GPIO.cleanup()

if __name__ == '__main__':
    display = LEDDisplay()
    try:
        display.start()
        while True:
            sleep(1)
    finally:
        display.stop()