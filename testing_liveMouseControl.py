import tkinter as tk

# Method created to work with action with Tkinter 
# Writing the X and Y position to the frame to know where you are
def show_mouse_position(event):
    position_label.config(text=f"Mouse Position: X={event.x}, Y={event.y}")

# Create the window to be edited 
root = tk.Tk()
root.title("Live Mouse Position")

# Writing the first intructions given on the window and let user know what to do
position_label = tk.Label(root, text="Move the mouse inside the window", font=('Arial', 14))
position_label.pack(pady=20)

# Action that tkinter understands and does the created motion associated with that action
root.bind('<Motion>', show_mouse_position)

# How to get it to excecute and run
root.mainloop()
