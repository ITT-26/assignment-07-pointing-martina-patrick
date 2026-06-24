# here goes your mediapipe-to-pointer implementation
import sys

import numpy as np
import cv2
from mediapipe.tasks.python import vision
from pynput.mouse import Button, Controller

from hand_detector.hand_detector import HandDetector


class PointingInput:
    def __init__(self, video_id = 0):
        self.cap = cv2.VideoCapture(video_id)
        self.frame = ...
        cv2.namedWindow('frame')
        # Init hand_detector.py
        self.hand_detector = HandDetector(vision.RunningMode.VIDEO)
        self.mouse = Controller()

    def start(self):
        while True:
            self.update()

            key = cv2.waitKey(1) & 0xFF

            self.handle_key_press(key)

    def handle_key_press(self, key):
        if key == ord('q'):
            self.stop()
            sys.exit(0)

    def update(self):
        ret, self.frame = self.cap.read()
        pointer, image = self.hand_detector.get_pointer_state(self.frame)
        cv2.imshow('frame',image)
        print(pointer)


    def simulate_mouse(self, x, y, clicked):
        self.mouse.position = (x, y)
        if clicked:
            self.mouse.click(Button.left, 1)

    def stop(self):
        self.cap.release()
        cv2.destroyAllWindows()


