import tkinter as tk
from tkinter import messagebox
import serial
import serial.tools.list_ports
import time

last_sent_time = 0
last_pos = [None, None]

# --- CONFIG ---
CNC_WIDTH = 600    # mm
CNC_HEIGHT = 900   # mm
GUI_WIDTH = 600    # pixels
GUI_HEIGHT = 900   # pixels
BAUD_RATE = 115200
# --------------

ser = None
mouse_control_enabled = False

def connect_serial():
    global ser
    try:
        ser = serial.Serial(port_entry.get(), BAUD_RATE, timeout=1)
        time.sleep(2)
        ser.reset_input_buffer()
        ser.write(b"$H\n")  # Home the machine
        log("Homing...")
        time.sleep(5)  # Wait for homing to finish (adjust if needed)

        ser.write(b"G91\n")  # Set to relative positioning
        log("Set to Relative Positioning (G91)")

        log("Connected to " + port_entry.get())
        connect_btn.config(state='disabled')
        disconnect_btn.config(state='normal')
        enable_btn.config(state='normal')
        home_btn.config(state='normal')
    except Exception as e:
        messagebox.showerror("Connection Failed", str(e))

def disconnect_serial():
    global ser
    if ser:
        ser.close()
        ser = None
        log("Disconnected")
    connect_btn.config(state='normal')
    disconnect_btn.config(state='disabled')
    enable_btn.config(state='disabled')
    home_btn.config(state='disabled')

def send_gcode(command):
    if ser and ser.is_open:
        print("Sending:", command)
        ser.write((command + '\n').encode())
        log(command)

def on_mouse_move(event):
    global last_sent_time, last_pos

    if not mouse_control_enabled:
        return

    x = max(0, min(event.x, GUI_WIDTH))
    y = max(0, min(event.y, GUI_HEIGHT))

    # Convert to mm with bottom-left origin
    x_mm = (x / GUI_WIDTH) * CNC_WIDTH
    y_mm = ((GUI_HEIGHT - y) / GUI_HEIGHT) * CNC_HEIGHT

    now = time.time()

    # Check distance threshold
    if last_pos[0] is not None:
        dx = abs(x_mm - last_pos[0])
        dy = abs(y_mm - last_pos[1])
        if dx < 0.5 and dy < 0.5:
            return

    # Send G1 move with feedrate
    gcode = f"G90 G21 G1 X{x_mm:.2f} Y{y_mm:.2f} F10000"
    send_gcode(gcode)

    coord_label.config(text=f"Target: X={x_mm:.1f} Y={y_mm:.1f}")
    last_sent_time = now
    last_pos = [x_mm, y_mm]

    # Throttle command rate to prevent GRBL overload
    # time.sleep(0.01)  # ~20 updates per second

def toggle_mouse_control():
    global mouse_control_enabled
    mouse_control_enabled = not mouse_control_enabled
    enable_btn.config(text="Disable Mouse" if mouse_control_enabled else "Enable Mouse")

def move_home():
    send_gcode("G90 G21 G1 X0 Y0 F10000")
    log("Moved to Home (relative zero)")

def log(text):
    log_text.insert(tk.END, text + '\n')
    log_text.see(tk.END)

def detect_ports():
    ports = [p.device for p in serial.tools.list_ports.comports()]
    if ports:
        port_entry.delete(0, tk.END)
        port_entry.insert(0, ports[0])
    else:
        port_entry.insert(0, "COM4")  # fallback

# --- GUI SETUP ---
root = tk.Tk()
root.title("CNC Mouse Control")

frame = tk.Frame(root)
frame.pack(pady=10)

tk.Label(frame, text="Port:").pack(side='left')
port_entry = tk.Entry(frame, width=10)
port_entry.pack(side='left')
detect_ports()

connect_btn = tk.Button(frame, text="Connect", command=connect_serial)
connect_btn.pack(side='left', padx=5)

disconnect_btn = tk.Button(frame, text="Disconnect", command=disconnect_serial, state='disabled')
disconnect_btn.pack(side='left')

enable_btn = tk.Button(frame, text="Enable Mouse", command=toggle_mouse_control, state='disabled')
enable_btn.pack(side='left', padx=5)

home_btn = tk.Button(frame, text="Go Home", command=move_home, state='disabled')
home_btn.pack(side='left')

coord_label = tk.Label(root, text="Relative Move: X=0 Y=0")
coord_label.pack()

canvas = tk.Canvas(root, width=GUI_WIDTH, height=GUI_HEIGHT, bg="white")
canvas.pack()
canvas.bind("<Motion>", on_mouse_move)

log_text = tk.Text(root, height=10, width=60)
log_text.pack(pady=10)

root.mainloop()
