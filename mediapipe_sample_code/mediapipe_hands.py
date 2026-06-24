# code from google mediapipe's code sample
# adapted to be compatible with opencv live image stream
# https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker/python

import sys
import cv2
import time
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from hand_landmark_drawer import draw_landmarks_on_image

#VIDEO_ID = int(sys.argv[1])
#NUM_HANDS = int(sys.argv[2])
MODEL_PATH = './hand_landmarker.task'

# Create an HandLandmarker object.
OPTIONS = vision.HandLandmarkerOptions(
    base_options=python.BaseOptions(model_asset_path=MODEL_PATH),
    num_hands=1,
    running_mode=vision.RunningMode.VIDEO,
    min_hand_detection_confidence=0.5,
    min_hand_presence_confidence=0.5,
    min_tracking_confidence=0.5
)
detector = vision.HandLandmarker.create_from_options(OPTIONS)

cap = cv2.VideoCapture(0)

while True:
    # Capture a frame from the webcam
    ret, frame = cap.read()

    # convert to mediapipe image
    mp_frame = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)

    # save current time for internal interpolation
    timestamp_ms = int(time.time() * 1000)

    # Detect hand landmarks from the input image.
    detection_result = detector.detect_for_video(mp_frame, timestamp_ms)

    # Process the classification result. In this case, visualize it.
    annotated_image = draw_landmarks_on_image(mp_frame.numpy_view(), detection_result)

    # show annotated image
    cv2.imshow("hand landmarks", annotated_image)

    # Wait for a key press and check if it's the 'q' key
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break


# Release the video capture object and close all windows
cap.release()
cv2.destroyAllWindows()