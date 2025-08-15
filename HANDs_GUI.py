import customtkinter
import cv2
from tkinter import *
from CTkMenuBar import *
from portManager import Ports
from PIL import Image, ImageTk

customtkinter.set_appearance_mode("dark")
customtkinter.set_default_color_theme('green')

class GUI(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.menu_bar = None
        self.title("HANDs Motion Control")
        self.geometry('900x600')
        self.minsize(800, 400)
        self.maxsize(1000, 800)

        self.cap = None
        self.cam_running = False
        self.cam_loop_id = None
        self.cam_img_ref = None

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
        self.close_cam_btn = customtkinter.CTkButton(
            self.cameraFrame, text="Close Camera", command=self.disable_camera_control
        )

        self.status = Label(self.statusFrame, text="FAMU-FSU Engineering Center",
                            bd=1, relief='sunken', anchor=W, font=('Tahoma', 15))
        self.status.pack(side='bottom', expand=True, anchor='s', fill='x')

        # Live coords label INSIDE interactiveFrame (this is the one that changes)
        self.coords_label = customtkinter.CTkLabel(
            self.interactiveFrame, text="Move the mouse inside the window", font=('Tahoma', 16)
        )
        self.coords_label.pack(anchor='nw', padx=10, pady=10)
        self.bind('<Motion>', self.show_mouse_position)

        # Creating the menu and options
        self.menu = CTkTitleMenu(self, padx=10, x_offset=425, y_offset=12)
        self.button_1 = self.menu.add_cascade("Comports", state='normal')
        self.button_2 = self.menu.add_cascade('Home Device', command=self.send_home, state='normal')
        self.button_3 = self.menu.add_cascade("E-Stop", command=self.eStop, state='normal')
        self.button_4 = self.menu.add_cascade("Camera Control", command=self.enable_camera_control, state='normal')
        self.button_5 = self.menu.add_cascade("Connect!", state='normal')

        self.port_manager = Ports()
        self.printing_port = self.port_manager.list_port()
        self.setPort = None
        self.eStopCounter = False

        # Listing the possible port options on start up and readies for connection
        self.dropdown1 = CustomDropdownMenu(widget=self.button_1, padx=2, pady=5, corner_radius=5, width=100)
        for x in self.printing_port:
            self.dropdown1.add_option(option=x, command=lambda r=x: self.set_port(r))

        # Give the option to connect or disconnect from COM device
        self.dropdown2 = CustomDropdownMenu(widget=self.button_5, padx=2, pady=5, corner_radius=5, width=100)
        self.dropdown2.add_option(option="Connect", command=self.connect_device)
        self.dropdown2.add_option(option="Disconnect", command=self.disconnect_device)


    def show_mouse_position(self, event):
        if not self.cam_running:
            self.coords_label.configure(text=f"Mouse Position: X={event.x}, Y={event.y}")


    def set_port(self, port):
        self.port_manager.comm_selection(port)
        print(f'{port} has been selected')


    def send_home(self):
        self.port_manager.send("G90 G21 G1 X0 Y0 F10000\n")
        print('Sending home')


    def eStop(self):
        self.eStopCounter = True
        self.button_3.configure(text='RESET', command=self.reset_device)
        self.lock_controls(True)
        self.port_manager.emergency_disconnet()
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


    def enable_camera_control(self):
        if self.cam_running:
            return
        # Pause mouse tracking while camera overlay is up
        self.unbind('<Motion>')
        self.cam_running = True
        self.button_4.configure(text='Close Camera', command=self.disable_camera_control, state='normal')

        # Show overlay above everything
        self.cameraFrame.place(relx=0, rely=0, relwidth=1, relheight=1)

        # Start camera
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # CAP_DSHOW helps on Windows
        if not self.cap.isOpened():
            print("Could not open camera.")
            self.disable_camera_control()
            return

        # Launch frame update loop
        self._camera_loop()
        print('Camera Enabled')


    def _camera_loop(self):
        if not self.cam_running or self.cap is None:
            return
        ok, frame = self.cap.read()
        if ok:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            im = Image.fromarray(rgb)
            im = im.resize((self.cameraFrame.winfo_width() or 800,
                            self.cameraFrame.winfo_height() or 600))
            tk_im = ImageTk.PhotoImage(im)
            self.cam_img_ref = tk_im  # keep ref
            self.cam_label.configure(image=tk_im)
        # update the frame every 10ms
        self.cam_loop_id = self.after(10, self._camera_loop)


    def disable_camera_control(self):
        # Hide camera overlay, stop capture, resume XY updates.
        # Stop loop
        if self.cam_loop_id is not None:
            self.after_cancel(self.cam_loop_id)
            self.cam_loop_id = None

        # Release camera
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None

        # Hide overlay and clear image
        self.cameraFrame.place_forget()
        self.cam_label.configure(image=None)
        self.cam_img_ref = None

        # Resume XY label updates
        self.cam_running = False
        self.bind('<Motion>', self.show_mouse_position)

        # Restore menu item
        self.button_4.configure(text="Camera Control", command=self.enable_camera_control, state='normal')
        print('Camera Closed — back to XY')


    def connect_device(self):
        self.port_manager.connect()
        print('Device connected')
        self.port_manager.send("$H\n")
        print('Homing the device...')
        

    def disconnect_device(self):
        self.port_manager.send("$H\n")
        print('Sending back home...')
        self.port_manager.disconnect()
        print('Device disconnect')

        
