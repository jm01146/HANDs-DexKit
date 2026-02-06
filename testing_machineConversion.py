"""
Trying to convert GUI pixels to machine code 
"""

import pyrealsense2 as rs

class Convertor():
    def __init__(self):
        super().__init__()
        # GUI parameters 
        self.gui_width = 2250  # pixels
        self.gui_length = 1500  # pixels
        # Gantry Config
        self.gantry_width = 600 # mm
        self.gantry_length = 800 # mm
        self.gantry_height = 400 # mm
        # Camera Config
        self.camera_width = 848 # pixels
        self.camera_length = 480 # pixels


    def guiToGantry(self, gui_X, gui_Y):
        scale_X = self.gantry_width / self.gui_width
        scale_Y = self.gantry_length / self.gui_length
        gantry_X = gui_X * scale_X
        gantry_Y = gui_Y * scale_Y
        return int(gantry_X), int(gantry_Y)
    

    def guiDepthToGantry(self, gui_Z):
        gantry_Z = max(0, min(gui_Z, self.gantry_height))
        return int(gantry_Z)


    def cameraToGantry(self, cam_X, cam_Y):
        scale_X = self.camera_width / self.gui_width
        scale_Y = self.camera_length / self.gui_length
        gantry_X = cam_X * scale_X
        gantry_Y = cam_Y * scale_Y
        return int(gantry_X), int(gantry_Y)
    

    def cameraDepthToGantry(self, cam_Z):
        gantry_Z = max(0, min((cam_Z * 1000), self.gantry_height))
        return int(gantry_Z)



# STUFF FOR AUTO CALIBRATE
# pipeline = rs.pipeline()
# config = rs.config()
# pipeline.start(config)
# profile = pipeline.get_active_profile()
# video_stream = profile.get_stream(rs.stream.color)
# intrinsics = video_stream.as_video_stream_profile().get_intrinsics()
# Camera config
# camera_width = intrinsics.width  # 848
# camera_length = intrinsics.height # 480
# print(f"Width: {camera_width}, Height: {camera_length}")
# pipeline.stop()


"""
Gcode notes: You must start every string with J$=
and it must follow with either a conditional code such as G
"""
