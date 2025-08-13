import pyrealsense2 as rs
import mediapipe as mp
import numpy as np
import cv2

# In the case of multiple RealSense cameras you can find all of them in this list and distribute that with different cams
# and config lines
ctx = rs.context()
rs_device = []
for rsItems in ctx.devices:
  rs_device.append(rsItems.get_info(rs.camera_info.serial_number))

# The cam and config lines that I mentioned above. If you need more, copy and paste. Just modify rs_device to count down the list
# and modify cam and config to differeciate which camera you are working with.
cam = rs.pipeline()
config = rs.config()
config.enable_device(rs_device[0])
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

# How to get the cam to actually work
cam.start(config)

# Initialize Mediapipe Hand Utilities
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

# Get the video feed and depth readings and display them
# Get the hand detection to work with the RealSense Depth camera
with mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0-.7) as hands:
    while True:

        # Gets the color and the depth information from the camera
        frames = cam.wait_for_frames()
        color_frame = frames.get_color_frame()
        depth_frame = frames.get_depth_frame()

        # Makes the information from previously into an array for CV2 to work with
        color_image = np.asarray(color_frame.get_data())
        depth_image = np.asarray(depth_frame.get_data())

        #Takes the color_image and sees if there is a hand there with its own dependicies
        results = hands.process(color_image)

        # If it sees a hands it will draw the landmarks such as fingers and palms in case you want to use them for gesture control
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(color_image, hand_landmarks, mp_hands.HAND_CONNECTIONS)


        cv2.imshow('Color Frame w/Hand Tacking', color_image)
        cv2.imshow('Depth Frame', depth_image)
    

# Waits for the user to hit the q button to close program #
        if cv2.waitKey(1) == ord('q'):
            break

# Allows to release the picture to free used system resources #
cam.stop()
cv2.destroyAllWindows()
