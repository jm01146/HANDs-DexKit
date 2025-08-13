from tkinter import *
import customtkinter
from CTkMenuBar import *

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
        self.mainFrame = customtkinter.CTkFrame(self)
        self.mainFrame.pack(side='top', expand=True, fill='both')
        self.statusFrame = customtkinter.CTkFrame(self)
        self.statusFrame.pack(side='bottom', fill='x')
        self.buttonsFrame = customtkinter.CTkFrame(master=self.mainFrame,
                                                   fg_color="#1B5633",
                                                   border_width=5,
                                                   border_color="#EE7624")
        self.buttonsFrame.grid_columnconfigure((0, 1, 2, 3, 4), weight=0)
        self.buttonsFrame.grid_rowconfigure((0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10), weight=0)
        self.buttonsFrame.pack(side='left', expand=True, fill='both')
        self.status = Label(self.statusFrame, text="FAMU-FSU Engineering Center",
                            bd=1, relief='sunken', anchor=W, font=('Tahoma', 15))
        self.status.pack(side='bottom', expand=True, anchor='s', fill='x')

        # Live coords label INSIDE buttonsFrame (this is the one that changes)
        self.coords_label = customtkinter.CTkLabel(
            self.buttonsFrame, text="Move the mouse inside the window", font=('Tahoma', 16)
        )
        self.coords_label.pack(anchor='nw', padx=10, pady=10)

        self.bind('<Motion>', self.show_mouse_position)

    def show_mouse_position(self, event):
        self.coords_label.configure(text=f"Mouse Position: X={event.x}, Y={event.y}")
