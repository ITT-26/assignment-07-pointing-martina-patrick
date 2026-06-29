# here goes your Fitts' Law application

import pyglet
import time
import math
import random
import pathlib
import cv2
import ctypes
from mediapipe.tasks.python import vision
from pynput.mouse import Controller
from collections import deque

from hand_detector.hand_detector import HandDetector
from hand_detector.pointer import Pointer

# window setup parameters
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 800

# design constants
TARGET_COLOR = (45, 130, 183)  # blue
CURRENT_TARGET_COLOR = (185, 98, 45)  # orange
POINTER_COLOR = (200, 50, 50)  # red
BODY_TEXT_COLOR = (255, 255, 255)  # white
COMMANDS_TEXT_COLOR = (0, 255, 0)  # green
BG_COLOR = (40, 40, 40)  # dark gray

TITLE_FONT_SIZE = 36
LARGE_FONT_SIZE = 30
SUBTITLE_FONT_SIZE = 26
INFO_FONT_SIZE = 22
SMALL_FONT_SIZE = 20

# other
DEQUE_LEN = 240


class FittsLawApp:
    def __init__(self, config: dict):

        # extract info from config file
        self.participant_id = config["participant_id"]
        self.conditions = config["conditions"]

        # log file
        self.log_file = None

        # state trackers
        self.current_condition_index = 0
        self.current_repetition = 0
        self.current_target_index = 0
        self.game_state = "init_screen"  # "init_screen", "trial_running", "repetition_complete", "condition_complete", "experiment_done"
        self.is_clicked = False
        self.pointer_buffer = deque(maxlen=DEQUE_LEN)  # [timestamp_ms, x, y]

        self.last_pose_x = WINDOW_WIDTH // 2
        self.last_pose_y = WINDOW_HEIGHT // 2
        self.pose_mouse = Controller()

        # condition-specific parameters
        self.input_method = None
        self.delay = None
        self.num_targets = None
        self.radius = None
        self.distance = None
        self.repetitions = None

        # screen and window setup
        self.window = pyglet.window.Window(
            width=WINDOW_WIDTH, height=WINDOW_HEIGHT, caption="Fitts' Law"
        )

        # extract screen width and height
        user32 = ctypes.windll.user32
        self.screen_width = user32.GetSystemMetrics(0)
        self.screen_height = user32.GetSystemMetrics(1)

        # bg color for pyglet interface
        pyglet.gl.glClearColor(*[c / 255.0 for c in BG_COLOR], 1.0)

        # callbacks
        self.window.on_draw = self.on_draw
        self.window.on_mouse_press = self.on_mouse_press
        self.window.on_key_press = self.on_key_press

        # pose detection setup
        self.hand_detector = None
        self.webcam = None
        self.show_camera_feed = (
            True  # True to show camera feed (useful for debugging) -- LABEL_DEBUG
        )
        self.cam_deadzone = 0.1

        # first (or only) condition setup
        self.setup_condition()  # here the current condition's condition-specific parameters are updated

        # pyglet update loop scheduling
        pyglet.clock.schedule_interval(self.update, 1 / 60.0)

    # picks a random target index to start the test, and pre-computes the whole index sequence
    # pairs index i with index i + num_targets/2 (the one across) - like the sample gif
    def random_start(self):
        num_targets = self.conditions[self.current_condition_index]["num_targets"]
        start = random.randint(
            0, num_targets - 1
        )  # pick a random target index as a starting point
        self.sequence = []
        for i in range(num_targets // 2):
            self.sequence.append((start + i) % num_targets)
            self.sequence.append((start + i + num_targets // 2) % num_targets)

    # update attributes (condition-specific parameters), setup camers (if needed), setup targets to draw later
    def setup_condition(self):
        self.input_method = self.conditions[self.current_condition_index][
            "input_method"
        ]
        self.delay = self.conditions[self.current_condition_index]["delay"]
        self.num_targets = self.conditions[self.current_condition_index]["num_targets"]
        self.radius = self.conditions[self.current_condition_index]["radius"]
        self.distance = self.conditions[self.current_condition_index]["distance"]
        self.repetitions = self.conditions[self.current_condition_index]["repetitions"]

        # camera initialization for pose input method
        if self.input_method == "pose" and self.webcam is None:
            self.webcam = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            self.hand_detector = HandDetector(vision.RunningMode.VIDEO)
            if self.show_camera_feed:
                cv2.namedWindow("Pose Debug")
        elif self.input_method != "pose" and self.webcam is not None:
            # release camera assets if moving to a non-pose condition
            self.cleanup_camera()

        # get center of the window
        center_x = WINDOW_WIDTH / 2
        center_y = WINDOW_HEIGHT / 2

        self.targets = []
        for n in range(self.num_targets):
            angle = (2 * math.pi * n) / self.num_targets
            x = center_x + (self.distance / 2) * math.cos(angle)
            y = center_y + (self.distance / 2) * math.sin(angle)
            circle = pyglet.shapes.Circle(x, y, self.radius, color=TARGET_COLOR)
            self.targets.append({"circle": circle, "x": x, "y": y, "index": n})

    # log file creation with header
    def setup_logging(self):
        pathlib.Path("results").mkdir(exist_ok=True)
        filename = (
            f"task_2_fitts_law/results/fitts_{self.participant_id}_{self.input_method}_"
            f"{self.delay}ms_{self.num_targets}_"
            f"{self.radius}_{self.distance}.csv"
        )
        self.log_file = open(filename, "w")
        self.log_file.write(
            "iteration,part_id,input_method,delay,num_targets,radius,distance,target_id,hit,timestamp\n"
        )
        self.log_file.flush()

    # new line in log file when click is detected
    def log_click(self, target_id, hit):
        timestamp = int(time.time() * 1000)  # in ms, abs timestamps
        self.log_file.write(
            f"{self.current_repetition},{self.participant_id},{self.input_method},{self.delay},"
            f"{self.num_targets},{self.radius},{self.distance},"
            f"{target_id},{1 if hit else 0},{timestamp}\n"
        )
        self.log_file.flush()

    # manages transitions to next repetition, condition, etc.
    def handle_transition(self):
        if self.current_target_index < self.num_targets - 1:
            # increment current target index
            self.current_target_index += 1
        elif self.current_target_index == self.num_targets - 1:
            if self.current_repetition < self.repetitions - 1:
                # increment current repetition
                self.current_repetition += 1
                # reset target index
                self.current_target_index = 0
                # setup new start
                self.random_start()
                self.game_state = "repetition_complete"
            else:
                if self.current_condition_index < len(self.conditions) - 1:
                    # increment current condition
                    self.current_condition_index += 1
                    # reset repetition tracker
                    self.current_repetition = 0
                    self.current_target_index = 0
                    # setup new condition and logging
                    self.setup_condition()
                    # close current file
                    if self.log_file:
                        self.log_file.close()
                    self.setup_logging()
                    self.game_state = "condition_complete"
                else:
                    self.game_state = "experiment_done"

    # moves through the sequence and updates the visuals accordingly
    def update_visuals(self, old_target):
        old_target["circle"].color = TARGET_COLOR
        if self.game_state == "trial_running":
            self.targets[self.sequence[self.current_target_index]][
                "circle"
            ].color = CURRENT_TARGET_COLOR

    def read_delayed(self, now, true_x, true_y):
        # target: timestamp [delay]ms ago
        target = now - self.delay

        # if the buffer is empty, return true coords. (first frame, nothing buffered yet)
        if not self.pointer_buffer:
            return true_x, true_y
        # if the oldest timestamp is still newer than the target, return oldest sample
        elif self.pointer_buffer[0][0] > target:
            return self.pointer_buffer[0][1], self.pointer_buffer[0][2]

        # it is very unlikely that we log a timestamp that is exactly = target:
        #   - intervals are scheduled at 60 fps (pyglet), so the buffer is sampled at discrete intervals also
        #   - time between two consectutive frames should be 1/60*1000 ~= 16.7 ms, but this isn't even the case
        #     because of how everything is handled in each OS, latency, etc.
        #   - 150 ms (delayed required in the assignment) is not a multiple of 16.7 ms
        #   - we are rounding the `now` variable

        # we try to find the two samples that enclose the actual value, and choose the nearest one

        # find index for which the timestamp is at or after target
        for i in range(len(self.pointer_buffer)):
            if self.pointer_buffer[i][0] >= target:
                break

        # target falls between before and after -> return whichever timestamp is nearer
        after = self.pointer_buffer[i]
        before = self.pointer_buffer[i - 1]
        if abs(after[0] - target) <= abs(before[0] - target):
            return after[1], after[2]
        else:
            return before[1], before[2]

    # push true pointer position into the buffer, update last position (attributes)
    def update_pointer(self, true_x, true_y):
        now = int(time.time() * 1000)
        self.pointer_buffer.append((now, true_x, true_y))  # push the true position
        self.last_pose_x, self.last_pose_y = self.read_delayed(
            now, true_x, true_y
        )  # read back the delayed position

    # check if click landed inside the target
    def handle_click(self, x, y):
        current_target = self.targets[self.sequence[self.current_target_index]]
        # calculate euclidean distance between center of the circle and the click coords.
        distance = math.sqrt(
            (x - current_target["x"]) ** 2 + (y - current_target["y"]) ** 2
        )

        target_id = current_target["index"]

        # if the calculated distance is smaller than the circle's radius, it means the click was inside the circle
        if distance <= self.radius:
            print("HIT!")  # -- LABEL_DEBUG
            # log hit
            self.log_click(target_id, hit=True)
            old_target = self.targets[self.sequence[self.current_target_index]]
            # handle transition to next target/end of repetition or condition
            self.handle_transition()
            # update screen
            self.update_visuals(old_target)
        else:
            print("MISS")  # -- LABEL_DEBUG
            # log miss
            self.log_click(target_id, hit=False)

    # call handle click on mouse press when trial is running
    def on_mouse_press(self, x, y, button, modifiers):
        if self.game_state == "trial_running":
            if self.input_method == "mouse" or self.input_method == "touchpad":
                if button == pyglet.window.mouse.LEFT:
                    self.handle_click(
                        self.last_pose_x, self.last_pose_y
                    )  # red dot instead of actual pointer for latency visualization

    # handle keyboard input
    def on_key_press(self, symbol, modifiers):
        # 'q' or [ESC] to quit
        if symbol == pyglet.window.key.Q or symbol == pyglet.window.key.ESCAPE:
            self.cleanup()
            pyglet.app.exit()
        # [SPACE] to advance through the trial
        elif symbol == pyglet.window.key.SPACE:
            if self.game_state == "init_screen":
                self.game_state = "condition_complete"
            elif self.game_state in ("repetition_complete", "condition_complete"):
                if self.game_state == "condition_complete":
                    self.setup_condition()
                    self.setup_logging()
                self.pointer_buffer.clear()
                self.random_start()
                self.targets[self.sequence[0]]["circle"].color = CURRENT_TARGET_COLOR
                self.game_state = "trial_running"

    # deadzone logic, taken from pointing_input.py
    def apply_deadzone(self, val, deadzone):
        val = max(deadzone, min(1 - deadzone, val))
        return (val - deadzone) / (1 - 2 * deadzone)

    # update - called every frame
    def update(self, dt):
        # MOUSE AND TOUCHPAD
        # track cursor position 
        if self.game_state == "trial_running" and (
            self.input_method == "mouse" or self.input_method == "touchpad"
        ):
            true_x, true_y = self.window._mouse_x, self.window._mouse_y
            self.update_pointer(true_x, true_y)  # push new position into buffer each frame

        # POSE
        if self.input_method == "pose" and self.game_state == "trial_running":
            frame_ok, frame = self.webcam.read()  # grab camera frame
            if not frame_ok:
                return

            # parse the camera frame
            pointer, annotated_image = self.hand_detector.get_pointer_state(frame)  # returns a normalized (x,y) pointer, annotated img

            if self.show_camera_feed:
                cv2.imshow("Pose Debug", annotated_image)  # camera feedback if show_camera_feed == True (for tests and debugging mainly)

            # invalid pointer check
            if pointer == Pointer.invalid_pointer():
                return

            # normalized pointer coords., taking into account deadzone (implemented in task 1 to reduce jitter)
            norm_x = self.apply_deadzone(pointer.x, self.cam_deadzone)
            norm_y = self.apply_deadzone(pointer.y, self.cam_deadzone)

            # multiply normalized coords by screen dimensions to get absolute pixel positions
            cursor_x = norm_x * self.screen_width
            cursor_y = norm_y * self.screen_height

            # initialize pynput mouse controller to move the desktop pointer
            if not hasattr(self, "pose_mouse"):
                self.pose_mouse = Controller()

            # move using abs coords.
            self.pose_mouse.position = (cursor_x, cursor_y)

            # get the pyglet window-relative cursor (after pynput), feed to delay buffer
            true_x, true_y = self.window._mouse_x, self.window._mouse_y
            self.update_pointer(true_x, true_y)

            # use pointer.clicked property to check for clicks
            # like in task 1, a held gesture only fires handle_click once, not every frame
            if pointer.clicked and not getattr(self, "is_clicked", False):
                self.handle_click(self.last_pose_x, self.last_pose_y)
                self.is_clicked = True
            elif not pointer.clicked:
                self.is_clicked = False

    # init screen
    def draw_init_screen(self):
        # title
        title = pyglet.text.Label(
            "Fitts' Law Test",
            x=WINDOW_WIDTH // 2,
            y=WINDOW_HEIGHT // 2 + 200,
            anchor_x="center",
            anchor_y="center",
            font_size=TITLE_FONT_SIZE,
            color=(*BODY_TEXT_COLOR, 255),
        )
        title.bold = True
        title.draw()

        # instructions
        pyglet.text.Label(
            "Point at and click on the orange target\nas fast as you can.",
            x=WINDOW_WIDTH // 2,
            y=WINDOW_HEIGHT // 2 + 50,
            anchor_x="center",
            anchor_y="center",
            font_size=SUBTITLE_FONT_SIZE,
            color=(*BODY_TEXT_COLOR, 255),
            multiline=True,
            width=600,
            align="center",
        ).draw()

        # show participant ID
        pyglet.text.Label(
            f"Participant ID: {self.participant_id}",
            x=WINDOW_WIDTH // 2,
            y=300,
            anchor_x="center",
            anchor_y="center",
            font_size=INFO_FONT_SIZE,
            color=(*BODY_TEXT_COLOR, 255),
        ).draw()

        # controls
        pyglet.text.Label(
            "[SPACE]: start/continue | 'q' / [ESC]: quit",
            x=WINDOW_WIDTH // 2,
            y=100,
            anchor_x="center",
            anchor_y="center",
            font_size=INFO_FONT_SIZE,
            color=(*COMMANDS_TEXT_COLOR, 255),
        ).draw()

    # repetition (iteration) complete screen
    def draw_rep_complete_screen(self):
        pyglet.text.Label(
            f"Repetition {self.current_repetition} of {self.repetitions} complete!",
            x=WINDOW_WIDTH // 2,
            y=WINDOW_HEIGHT // 2 + 50,
            anchor_x="center",
            anchor_y="center",
            font_size=LARGE_FONT_SIZE,
            color=(*BODY_TEXT_COLOR, 255),
        ).draw()

        pyglet.text.Label(
            "Press [SPACE] to continue",
            x=WINDOW_WIDTH // 2,
            y=100,
            anchor_x="center",
            anchor_y="center",
            font_size=INFO_FONT_SIZE,
            color=(*COMMANDS_TEXT_COLOR, 255),
        ).draw()

    # new condition screen
    def draw_condition_screen(self):
        # title
        pyglet.text.Label(
            f"Condition {self.current_condition_index + 1} of {len(self.conditions)}:",
            x=WINDOW_WIDTH // 2,
            y=WINDOW_HEIGHT // 2 + 250,
            anchor_x="center",
            anchor_y="center",
            font_size=LARGE_FONT_SIZE,
            color=(*BODY_TEXT_COLOR, 255),
        ).draw()

        # input method (large and highlighted since it's important for the user if the condition changes)
        pyglet.text.Label(
            f"Input: {self.input_method}",
            x=WINDOW_WIDTH // 2,
            y=WINDOW_HEIGHT // 2 + 150,
            anchor_x="center",
            anchor_y="center",
            font_size=SUBTITLE_FONT_SIZE - 2,
            color=TARGET_COLOR,
        ).draw()

        # delay
        pyglet.text.Label(
            f"Delay: {self.delay} ms",
            x=WINDOW_WIDTH // 2,
            y=WINDOW_HEIGHT // 2 + 80,
            anchor_x="center",
            anchor_y="center",
            font_size=INFO_FONT_SIZE,
            color=(*BODY_TEXT_COLOR, 255),
        ).draw()

        # task parameters
        pyglet.text.Label(
            f"Targets: {self.num_targets}  |  Radius: {self.radius}  |  Distance: {self.distance}",
            x=WINDOW_WIDTH // 2,
            y=WINDOW_HEIGHT // 2 + 20,
            anchor_x="center",
            anchor_y="center",
            font_size=INFO_FONT_SIZE,
            color=(*BODY_TEXT_COLOR, 255),
        ).draw()

        # repetitions
        pyglet.text.Label(
            f"You will need to repeat this task {self.repetitions} times.",
            x=WINDOW_WIDTH // 2,
            y=WINDOW_HEIGHT // 2 - 100,
            anchor_x="center",
            anchor_y="center",
            font_size=INFO_FONT_SIZE,
            color=BODY_TEXT_COLOR,
        ).draw()

        # instructions
        pyglet.text.Label(
            "Press [SPACE] to start",
            x=WINDOW_WIDTH // 2,
            y=100,
            anchor_x="center",
            anchor_y="center",
            font_size=INFO_FONT_SIZE,
            color=(*COMMANDS_TEXT_COLOR, 255),
        ).draw()

    # experiment done screen
    def draw_exp_done_screen(self):
        pyglet.text.Label(
            "Experiment complete!",
            x=WINDOW_WIDTH // 2,
            y=WINDOW_HEIGHT // 2 + 100,
            anchor_x="center",
            anchor_y="center",
            font_size=LARGE_FONT_SIZE,
            color=(*BODY_TEXT_COLOR, 255),
        ).draw()
        pyglet.text.Label(
            "Thank you for participating.",
            x=WINDOW_WIDTH // 2,
            y=WINDOW_HEIGHT // 2 + 20,
            anchor_x="center",
            anchor_y="center",
            font_size=INFO_FONT_SIZE,
            color=(*BODY_TEXT_COLOR, 255),
        ).draw()
        pyglet.text.Label(
            "'q' / [ESC]: quit",
            x=WINDOW_WIDTH // 2,
            y=100,
            anchor_x="center",
            anchor_y="center",
            font_size=INFO_FONT_SIZE,
            color=(*COMMANDS_TEXT_COLOR, 255),
        ).draw()

    # info that is shown while trial is running
    def draw_hud(self):
        # repetition
        pyglet.text.Label(
            f"Rep: {self.current_repetition + 1}/{self.repetitions}",
            x=WINDOW_WIDTH - 10,
            y=WINDOW_HEIGHT - 30,
            anchor_x="right",
            anchor_y="center",
            font_size=SMALL_FONT_SIZE,
            color=(*BODY_TEXT_COLOR, 255),
        ).draw()

        # condition
        pyglet.text.Label(
            f"Condition: {self.current_condition_index + 1}/{len(self.conditions)}",
            x=10,
            y=WINDOW_HEIGHT - 30,
            anchor_x="left",
            anchor_y="center",
            font_size=SMALL_FONT_SIZE,
            color=(*BODY_TEXT_COLOR, 255),
        ).draw()

        # input method
        pyglet.text.Label(
            f"Input method: {self.input_method}",
            x=10,
            y=30,
            anchor_x="left",
            anchor_y="center",
            font_size=SMALL_FONT_SIZE,
            color=(*BODY_TEXT_COLOR, 255),
        ).draw()

    # draw
    def on_draw(self):
        self.window.clear()
        if self.game_state == "trial_running":
            for target in self.targets:
                target["circle"].draw()

            if hasattr(self, "last_pose_x"):
                pointer_dot = pyglet.shapes.Circle(
                    self.last_pose_x, self.last_pose_y, 10, color=(255, 0, 0)
                )
                pointer_dot.draw()

            self.draw_hud()
        elif self.game_state == "init_screen":
            self.draw_init_screen()
        elif self.game_state == "repetition_complete":
            self.draw_rep_complete_screen()
        elif self.game_state == "condition_complete":
            self.draw_condition_screen()
        elif self.game_state == "experiment_done":
            self.draw_exp_done_screen()

    # cleanup
    def cleanup_camera(self):
        if self.webcam:
            self.webcam.release()
            self.webcam = None
        if self.show_camera_feed:
            try:
                cv2.destroyWindow("Pose Debug")
            except cv2.error:
                pass

    # cleanup
    def cleanup(self):
        self.cleanup_camera()
        if self.log_file:
            self.log_file.close()
