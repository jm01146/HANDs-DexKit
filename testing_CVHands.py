import cv2
import mediapipe as mp

# Initialize MediaPipe Hands and Drawing utilities
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

ID8_IndexTip = 8
ID5_IndexMCP = 5


# Start video capture
cap = cv2.VideoCapture(0)

with mp_hands.Hands(static_image_mode=False, max_num_hands=2, min_detection_confidence=0.5) as hands:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Convert the frame to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        h, w = frame.shape[:2]

        # Process the frame to detect hands
        results = hands.process(rgb_frame)

        # Draw hand landmarks if detected
        if results.multi_hand_landmarks:
            for hand_idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                ID8 = hand_landmarks.landmark[ID8_IndexTip]
                ID5 = hand_landmarks.landmark[ID5_IndexMCP]
                px2, py2 = int(ID8.x * w), int(ID8.y * h)
                px1, py1 = int(ID5.x * w), int(ID5.y * h)
                # FOR DEBUGGING AND TESTING PURPOSES ONLY
                # print(f"Point Name: {mp_hands.HandLandmark(ID5_Index).name}, Pixels (x,y): {px, py}")
                print(f"ID8(x2,y2): {px2, py2}, ID5(x1,y1): {px1, py1}")

        # Display the frame
        cv2.imshow('Hand Landmarks', frame)

        # Exit on pressing 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

# Release resources
cap.release()
cv2.destroyAllWindows()
