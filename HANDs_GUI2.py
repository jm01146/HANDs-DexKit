import customtkinter
import threading
import cv2
import serial
import numpy as np
import pyrealsense2 as rs
import mediapipe as mp
from tkinter import *
from CTkMenuBar import *
from portManager import Ports
from testing_machineConversion import Convertor
from PIL import Image, ImageTk
import time


customtkinter.set_appearance_mode("dark")
customtkinter.set_default_color_theme('green')


def ema(prev, new, alpha=0.4):
    return (1 - alpha) * prev + alpha * new if prev is not None else new


class GUI(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.menu_bar = None
        self.title("HANDs Motion Control")
        self.geometry('900x600')
        self.minsize(800, 400)
        self.maxsize(1000, 800)

        self.x, self.y, self.z = 0, 0, 0
        self.command_x, self.command_y, self.command_z = 0, 0, 0
        self.convert = Convertor()

        self.mainFrame = customtkinter.CTkFrame(self)
        self.mainFrame.pack(side='top', expand=True, fill='both')
        self.statusFrame = customtkinter.CTkFrame(self)
        self.statusFrame.pack(side='bottom', fill='x')
        self.interactiveFrame = customtkinter.CTkFrame(master=self.mainFrame,
                                                   fg_color="#1B5633",
                                                   border_width=5,
                                                   border_color="#EE7624")
        self.interactiveFrame.grid_columnconfigure((0, 1, 2, 3, 4), weight=0)
        self.interactiveFrame.grid_rowconfigure((0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10), weight=0)
        self.interactiveFrame.pack(side='left', expand=True, fill='both')

        self.cameraFrame = customtkinter.CTkFrame(master=self.mainFrame, fg_color='#000000')
        self.cameraFrame.place_forget()
        self.cam_label = customtkinter.CTkLabel(self.cameraFrame, text="")
        self.cam_label.pack(expand=True, fill='both', padx=10, pady=10)

        self.status = Label(self.statusFrame, text="FAMU-FSU Engineering Center",
                            bd=1, relief='sunken', anchor=W, font=('Tahoma', 15))
        self.status.pack(side='bottom', expand=True, anchor='s', fill='x')

        # Live coords label INSIDE interactiveFrame (this is the one that changes)
        self.coords_label = customtkinter.CTkLabel(
            self.interactiveFrame, text="Move the mouse inside the window", font=('Tahoma', 16)
        )
        self.coords_label.pack(anchor='nw', padx=10, pady=10)

        # Values received from the second microcontroller
        self.sensor_value_1 = customtkinter.StringVar(value="Variable 1: --")
        self.sensor_value_2 = customtkinter.StringVar(value="Variable 2: --")

        self.sensor_label_1 = customtkinter.CTkLabel(self.interactiveFrame, textvariable=self.sensor_value_1,
                                                 font=("Tahoma", 18))
        self.sensor_label_1.pack(anchor="nw", padx=10, pady=(20, 5))

        self.sensor_label_2 = customtkinter.CTkLabel(self.interactiveFrame, textvariable=self.sensor_value_2,
                                                     font=("Tahoma", 18))
        self.sensor_label_2.pack(anchor="nw", padx=10, pady=5)

        # Creating the menu and options
        self.menu = CTkTitleMenu(self, padx=10, x_offset=425, y_offset=12)
        self.button_1 = self.menu.add_cascade("Comports", state='normal')
        self.button_2 = self.menu.add_cascade('Home Device', command=self.send_home, state='normal')
        self.button_3 = self.menu.add_cascade("E-Stop", command=self.eStop, state='normal')
        self.button_5 = self.menu.add_cascade("Connect!", state='normal')

        self.port_manager = Ports()
        self.printing_port = self.port_manager.list_port()
        self.setPort = None
        self.eStopCounter = False

                # Sensor serial port
        self.data_serial = None
        self.data_port_name = "COM3"
        self.data_baudrate = 115200

        # Sensor-reading thread
        self.sensor_thread = None
        self.sensor_stop_event = threading.Event()
        self.sensor_lock = threading.Lock()

        # Latest cumulative sensor position
        self.latest_sensor_position = None
        self.previous_sensor_position = None

        # Motion-control settings
        self.control_period_ms = 100     # Maximum 10 jog commands per second
        self.sensor_deadband_mm = 0.05   # Ignore tiny movements/noise
        self.sensor_gain = 1.0           # Increase/decrease sensor sensitivity
        self.max_step_mm = 3.0           # Maximum movement per command
        self.jog_feed = 600              # Start slowly while testing

        # Change these if an axis moves backward
        self.invert_sensor_x = False
        self.invert_sensor_y = True

        self.open_data_port()

        # Runs on the Tkinter thread
        self.after(self.control_period_ms, self.update_machine_from_sensor)

        # Listing the possible port options on start up and readies for connection
        self.dropdown1 = CustomDropdownMenu(widget=self.button_1, padx=2, pady=5, corner_radius=5, width=100)
        for x in self.printing_port:
            self.dropdown1.add_option(option=x, command=lambda r=x: self.set_port(r))

        # Give the option to connect or disconnect from COM device
        self.dropdown2 = CustomDropdownMenu(widget=self.button_5, padx=2, pady=5, corner_radius=5, width=100)
        self.dropdown2.add_option(option="Connect", command=self.connect_device)
        self.dropdown2.add_option(option="Disconnect", command=self.disconnect_device)

        self.protocol("WM_DELETE_WINDOW", self.on_close)


    def set_port(self, port):
        self.port_manager.comm_selection(port)
        print(f'{port} has been selected')


    def send_home(self):
        self.port_manager.send("$H\n")
        print('Sending home')


    def eStop(self):
        self.eStopCounter = True
        self.button_3.configure(text='RESET', command=self.reset_device)
        self.lock_controls(True)
        self.port_manager.emergency_disconnect()
        print('OH SHIT!')
        print('Please reset before sending commands')


    def reset_device(self):
        self.eStopCounter = False
        self.button_3.configure(text='E-Stop', command=self.eStop)
        self.lock_controls(False)
        self.port_manager.connect()
        print('Back in motion')
        print('Back to the mission...')


    def lock_controls(self, locked=True):
        state = "disabled" if locked else "normal"
        self.button_1.configure(state=state)
        self.button_2.configure(state=state)
        self.button_4.configure(state=state)
        self.button_5.configure(state=state)


    def connect_device(self):
        self.port_manager.connect()
        print('Device connected')
        # self.port_manager.send("$H\n")
        # print('Homing the device...')
        

    def disconnect_device(self):
        # self.port_manager.send("$H\n")
        # print('Sending back home...')
        self.port_manager.disconnect()
        print('Device disconnect')


    def on_close(self):
        try:
            self.disable_camera_control()
        except Exception:
           pass

        try:
            self.close_data_port()
        except Exception:
            pass

        try:
            self.port_manager.disconnect()
        except Exception:
            pass

        self.destroy()



    def open_data_port(self):
        """Open the sensor port and start its background reader."""
        try:
            self.data_serial = serial.Serial(
                port=self.data_port_name,
                baudrate=self.data_baudrate,
                timeout=0.1
            )

            self.data_serial.reset_input_buffer()
            self.sensor_stop_event.clear()

            self.sensor_thread = threading.Thread(
                target=self.sensor_reader,
                daemon=True
            )
            self.sensor_thread.start()

            print(f"Sensor connected on {self.data_port_name}")
            self.status.configure(
                text=f"Sensor connected: {self.data_port_name}"
            )

        except serial.SerialException as error:
            self.data_serial = None
            print(f"Could not open sensor port: {error}")
            self.status.configure(text="Sensor connection failed")


    def sensor_reader(self):
        """
        Read sensor data outside the Tkinter thread.

        Only the newest position is saved. Old readings are automatically
        discarded, preventing a growing backlog.
        """
        while not self.sensor_stop_event.is_set():
            try:
                if self.data_serial is None or not self.data_serial.is_open:
                    break

                raw_data = self.data_serial.readline()

                if not raw_data:
                    continue

                line = raw_data.decode(
                    "utf-8",
                    errors="ignore"
                ).strip()

                parts = line.split(",")

                if len(parts) != 2:
                    # Ignores PMW3389 startup messages
                    continue

                try:
                    sensor_x = float(parts[0].strip())
                    sensor_y = float(parts[1].strip())
                except ValueError:
                    continue

                # Do not touch Tkinter widgets from this thread
                with self.sensor_lock:
                    self.latest_sensor_position = (sensor_x, sensor_y)

            except serial.SerialException as error:
                if not self.sensor_stop_event.is_set():
                    print(f"Sensor read error: {error}")
                break

            except Exception as error:
                print(f"Unexpected sensor error: {error}")


    def update_machine_from_sensor(self):
        """
        Runs on the Tkinter thread.

        Converts the cumulative sensor position into relative machine motion
        and sends at most one jog command per control period.
        """
        try:
            with self.sensor_lock:
                current_position = self.latest_sensor_position

            if current_position is None:
                return

            sensor_x, sensor_y = current_position

            # Safe because this method runs on the Tkinter thread
            self.sensor_value_1.set(f"Sensor X: {sensor_x:.3f} mm")
            self.sensor_value_2.set(f"Sensor Y: {sensor_y:.3f} mm")

            # Establish the first sensor position without moving the machine
            if self.previous_sensor_position is None:
                self.previous_sensor_position = current_position
                return

            previous_x, previous_y = self.previous_sensor_position

            # Sensor values are cumulative, so calculate the change
            delta_x = (sensor_x - previous_x) * self.sensor_gain
            delta_y = (sensor_y - previous_y) * self.sensor_gain

            # Always update this, even while the machine is disconnected.
            # This prevents a huge jump when it reconnects.
            self.previous_sensor_position = current_position

            if self.invert_sensor_x:
                delta_x = -delta_x

            if self.invert_sensor_y:
                delta_y = -delta_y

            # Ignore optical noise and tiny accidental movements
            if abs(delta_x) < self.sensor_deadband_mm:
                delta_x = 0.0

            if abs(delta_y) < self.sensor_deadband_mm:
                delta_y = 0.0

            if delta_x == 0.0 and delta_y == 0.0:
                return

            # Protect against corrupted readings or sudden sensor jumps
            delta_x = max(
                -self.max_step_mm,
                min(delta_x, self.max_step_mm)
            )
            delta_y = max(
                -self.max_step_mm,
                min(delta_y, self.max_step_mm)
            )

            if self.eStopCounter:
                return

            if not self.port_manager.serialInst.is_open:
                return

            axes = []

            if delta_x != 0.0:
                axes.append(f"X{delta_x:.3f}")

            if delta_y != 0.0:
                axes.append(f"Y{delta_y:.3f}")

            axis_commands = " ".join(axes)
            print(axis_commands)

            # G91 = relative movement
            # G21 = millimeters
            command = (
                f"$J=G91 G21 {axis_commands} "
                f"F{self.jog_feed}\n"
            )

            self.port_manager.send(command)

            # Do not print every sensor reading here.
            # Printing hundreds of lines can noticeably slow the application.

        except serial.SerialException as error:
            print(f"Machine communication error: {error}")
            self.status.configure(text="Machine communication error")

        except Exception as error:
            print(f"Sensor control error: {error}")

        finally:
            # Schedule exactly one future control update
            if self.winfo_exists():
                self.after(
                    self.control_period_ms,
                    self.update_machine_from_sensor
                )


    def close_data_port(self):
        """Stop the sensor thread and close its serial connection."""
        self.sensor_stop_event.set()

        if self.data_serial is not None:
            try:
                if self.data_serial.is_open:
                    self.data_serial.close()

            except serial.SerialException as error:
                print(f"Error closing sensor port: {error}")

        if (
            self.sensor_thread is not None
            and self.sensor_thread.is_alive()
        ):
            self.sensor_thread.join(timeout=0.3)

        print("Sensor port closed")

    
