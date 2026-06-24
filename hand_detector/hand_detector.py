import math
import os
from typing import Any

import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from numpy import dtype, generic, ndarray

from hand_detector.pointer import Pointer

import cv2
import time

class HandDetector:

    def __init__(self, mode: vision.RunningMode = vision.RunningMode.VIDEO):
        # Use this to select the mode for mp
        self.mode = mode
        self.mp_hands = mp.tasks.vision.HandLandmarksConnections
        self.mp_drawing = mp.tasks.vision.drawing_utils
        self.mp_drawing_styles = mp.tasks.vision.drawing_styles

        # print(os.getcwd()) Debug purposes

        #Init Mediapipe stuff
        model_path = 'hand_detector/hand_landmarker.task'

        # Create an HandLandmarker object.
        options = vision.HandLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=model_path),
            num_hands=1,
            running_mode=mode,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )

        self.detector = vision.HandLandmarker.create_from_options(options)

        self.pointer = Pointer(-99, -99, False)

    def get_pointer_state(self, frame):
        mp_frame = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)

        # save current time for internal interpolation
        timestamp_ms = int(time.time() * 1000)

        # Detect hand landmarks from the input image.
        detection_result = self.detector.detect_for_video(mp_frame, timestamp_ms)

        image = self._annotate_image(mp_frame.numpy_view(), detection_result)
        pointer = self._extract_pointer_data(mp_frame.numpy_view(), detection_result)

        return pointer, image

    def _annotate_image(self, rgb_image, detection_result):
        hand_landmarks_list = detection_result.hand_landmarks
        handedness_list = detection_result.handedness
        annotated_image = np.copy(rgb_image)
        # Loop through the detected hands to visualize.
        for idx in range(len(hand_landmarks_list)):
            hand_landmarks = hand_landmarks_list[idx]
            handedness = handedness_list[idx]

            # Draw the hand landmarks.
            self.mp_drawing.draw_landmarks(
                annotated_image,
                hand_landmarks,
                self.mp_hands.HAND_CONNECTIONS,
                self.mp_drawing_styles.get_default_hand_landmarks_style(),
                self.mp_drawing_styles.get_default_hand_connections_style()
            )

            # Get the top left corner of the detected hand's bounding box.
            height, width, _ = annotated_image.shape
            x_coordinates = [landmark.x for landmark in hand_landmarks]
            y_coordinates = [landmark.y for landmark in hand_landmarks]
            text_x = int(min(x_coordinates) * width)
            text_y = int(min(y_coordinates) * height) - 10

            # Draw handedness (left or right hand) on the image.
            cv2.putText(annotated_image, f"{handedness[0].category_name}",
                        (text_x, text_y), cv2.FONT_HERSHEY_DUPLEX,
                        1, (88, 205, 54), 1, cv2.LINE_AA)

        return annotated_image


    def _extract_pointer_data(self, rgb_image, detection_result) -> Pointer:
        hand_landmarks_list = detection_result.hand_landmarks
        # Loop through the detected hands to visualize.
        for idx in range(len(hand_landmarks_list)):
            hand_landmarks = hand_landmarks_list[idx]

            thumb_tip = hand_landmarks[4]
            index_tip = hand_landmarks[8]
            middle_tip = hand_landmarks[12]

            distance_middle_thumb = self.distance_between(middle_tip, thumb_tip)
            # Returns a percentage, meaning the top left point is 0, 0 and bottom right is 0, 0
            # Flip the X coord so it is actually correct and adjusts for the flipped camera image
            return Pointer((index_tip.x * -1) + 1, index_tip.y, distance_middle_thumb < 0.02)
        return Pointer.invalid_pointer()



    def distance_between(self, landmark, other):
        return math.sqrt((landmark.x - other.x) ** 2 + (landmark.y - other.y) ** 2)