# Importing Libraries
import serial.tools.list_ports
import re


# Creating the Ports class for the GUI to use
class Ports(serial.Serial):
    def __init__(self):
        super().__init__()
        # Taking serialInst and scanningPorts as Objects that have the properties of Serial Functions
        self.serialInst = serial.Serial()
        
        # Setting the initial values that will be gathered from the GUI
        self.serialInst.baudrate = 115200
        self.portName = None
        self.portList = None
        self.com = None


    # Making a function that prints all the ports
    def list_port(self):
        scanningPorts = serial.tools.list_ports.comports()
        ports_listed = []
        for ports in scanningPorts:
            ports_listed.append(str(ports))
        self.portList = ports_listed[:]
        return self.portList


    # Way for the GUI to select the COM channel
    def comm_selection(self, gui_com):
        self.com = gui_com
        match = re.search(r'COM(\d+)', self.com)
        if match:
            self.com = str(match.group())


    # Way for the GUI to connect to device
    def connect(self):
        self.serialInst.port = self.com
        self.serialInst.open()


    # Way for the GUI to send commands to device
    def send(self, command):
        self.serialInst.write(command.encode())


    # Way for the GUI to disconnect from the device
    def disconnect(self):
        self.serialInst.close()


    def emergency_disconnet(self):
        self.serialInst.reset_input_buffer()
        self.serialInst.close()
