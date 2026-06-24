# here goes your mediapipe-to-pointer implementation
import sys

import numpy as np
import cv2
from mediapipe.tasks.python import vision
from pynput.mouse import Button, Controller
import ctypes

from hand_detector.hand_detector import HandDetector
from hand_detector.pointer import Pointer


class PointingInput:
    def __init__(self,  camera_deadzone, video_id = 0, camera=False):
        self.cap = cv2.VideoCapture(video_id)
        self.displays_img = camera
        if self.displays_img:
            cv2.namedWindow('frame')
        # Init hand_detector.py
        self.hand_detector = HandDetector(vision.RunningMode.VIDEO)
        self.mouse = Controller()
        self.screen_dimensions = self._get_screen_dims()
        self.is_clicked = False
        self.cam_deadzone = .1 if camera_deadzone is None else camera_deadzone


    def _get_screen_dims(self):
        # Source - https://stackoverflow.com/a/3129524
        # Posted by jcao219, modified by community. See post 'Timeline' for change history
        # Retrieved 2026-06-24, License - CC BY-SA 4.0

        user32 = ctypes.windll.user32
        screensize = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
        return screensize

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
        if self.displays_img:
            cv2.imshow("frame", image)
        if pointer == Pointer.invalid_pointer():
            return
        screen_x, screen_y = self.convert_relative_pos_to_absolute_pos(pointer.x, pointer.y)
        sim_click = pointer.clicked and not self.is_clicked
        self.simulate_mouse(screen_x, screen_y, sim_click)
        if not pointer.clicked:
            self.is_clicked = False

    def convert_relative_pos_to_absolute_pos(self, relative_x, relative_y):
        relative_x = self._apply_deadzone(relative_x)
        relative_y = self._apply_deadzone(relative_y)
        abs_x = relative_x * self.screen_dimensions[0]
        abs_y = relative_y * self.screen_dimensions[1]
        return abs_x, abs_y


    def _apply_deadzone(self, val):
        val = max(self.cam_deadzone, min(1 - self.cam_deadzone, val))
        val = (val - self.cam_deadzone) / (1 - 2 * self.cam_deadzone)
        return val

    def simulate_mouse(self, x, y, sim_click):
        self.mouse.position = (x, y)
        if sim_click:
            self.mouse.click(Button.left, 1)
            self.is_clicked = True

    def stop(self):
        self.cap.release()
        cv2.destroyAllWindows()


