# here goes your Steering Law application

import pyglet
import time
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

WALL_THICKNESS = 20
ZONE_WIDTH = 20
START_END_THICKNESS = 3

# other
DEQUE_LEN = 240
DEFAULT_DATA_DIR = "task_3_steering_law/data"


class SteeringLawApp:
    def __init__(self, config: dict):

        # extract info from config file
        self.participant_id = config["participant_id"]
        self.conditions = config["conditions"]
        self.data_dir = config.get("output_dir", DEFAULT_DATA_DIR)

        # log file
        self.log_file = None

        # state trackers
        self.current_condition_index = 0
        self.current_repetition = 0
        self.current_errors = 0  # wall touches in the current traversal
        self.trial_start_time = None  # set when pointer enters the start zone
        self.pointer_inside = False  # was the pointer inside the tunnel on the previous frame? (for error counting)
        self.game_state = "init_screen"  # "init_screen", "waiting_start", "trial_running", "repetition_complete", "condition_complete", "experiment_done"
        self.pointer_buffer = deque(maxlen=DEQUE_LEN)  # [timestamp_ms, x, y]

        self.last_pose_x = WINDOW_WIDTH // 2
        self.last_pose_y = WINDOW_HEIGHT // 2
        self.pose_mouse = Controller()

        # condition-specific parameters
        self.input_method = None
        self.delay = None
        self.width = None
        self.distance = None
        self.repetitions = None

        # screen and window setup
        self.window = pyglet.window.Window(
            width=WINDOW_WIDTH, height=WINDOW_HEIGHT, caption="Steering Law"
        )

        # extract screen width and height
        user32 = ctypes.windll.user32
        self.screen_width = user32.GetSystemMetrics(0)
        self.screen_height = user32.GetSystemMetrics(1)

        # bg color for pyglet interface
        pyglet.gl.glClearColor(*[c / 255.0 for c in BG_COLOR], 1.0)

        # some params that are worth setting as attributes for drawing elements and labels
        self.center_x = WINDOW_WIDTH / 2
        self.center_y = WINDOW_HEIGHT / 2
        self.tunnel_left = None
        self.tunnel_right = None
        self.wall_bottom_y = None
        self.wall_top_y = None

        # callbacks 
        self.window.on_draw = self.on_draw
        self.window.on_key_press = self.on_key_press

        # pose detection setup
        self.hand_detector = None
        self.webcam = None
        self.show_camera_feed = True  # True to show camera feed (useful for debugging) -- LABEL_DEBUG
        self.cam_deadzone = 0.1

        # first (or only) condition setup
        self.setup_condition()  # here the current condition's condition-specific parameters are updated

        # pyglet update loop scheduling
        pyglet.clock.schedule_interval(self.update, 1 / 60.0)

    # update attributes (condition-specific parameters), setup camera (if needed), build the tunnel geometry to draw later
    def setup_condition(self):
        self.input_method = self.conditions[self.current_condition_index][
            "input_method"
        ]
        self.delay = self.conditions[self.current_condition_index]["delay"]
        self.width = self.conditions[self.current_condition_index]["width"]
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

        # tunnel geometry: a horizontal corridor centered in the window
        # distance = horizontal length of the tunnel, width = vertical gap between the walls
        self.tunnel_left = self.center_x - self.distance / 2
        self.tunnel_right = self.center_x + self.distance / 2
        self.wall_bottom_y = self.center_y - self.width / 2
        self.wall_top_y = self.center_y + self.width / 2

        # walls
        self.wall_bottom = pyglet.shapes.Rectangle(
            x=self.tunnel_left,
            y=self.wall_bottom_y - WALL_THICKNESS,
            width=self.distance,
            height=WALL_THICKNESS,
            color=TARGET_COLOR,
        )
        self.wall_top = pyglet.shapes.Rectangle(
            x=self.tunnel_left,
            y=self.wall_top_y,
            width=self.distance,
            height=WALL_THICKNESS,
            color=TARGET_COLOR,
        )

        # start (left, green) and end (right, orange) lines
        self.start_line = pyglet.shapes.Line(
            self.tunnel_left,
            self.wall_bottom_y,
            self.tunnel_left,
            self.wall_top_y,
            thickness=START_END_THICKNESS,
            color=COMMANDS_TEXT_COLOR,
        )
        self.end_line = pyglet.shapes.Line(
            self.tunnel_right,
            self.wall_bottom_y,
            self.tunnel_right,
            self.wall_top_y,
            thickness=START_END_THICKNESS,
            color=CURRENT_TARGET_COLOR,
        )

    # log file creation with header
    def setup_logging(self):
        pathlib.Path(self.data_dir).mkdir(parents=True, exist_ok=True)
        filename = pathlib.Path(self.data_dir) / (
            f"steering_{self.participant_id}_{self.input_method}_"
            f"{self.delay}ms_{self.width}_{self.distance}.csv"
        )
        self.log_file = open(filename, "w")
        self.log_file.write(
            "iteration,part_id,input_method,delay,width,distance,errors,start_time,end_time\n"
        )
        self.log_file.flush()

    # new line in log file: one row per completed tunnel
    def log_trial(self, start_time, end_time):
        self.log_file.write(
            f"{self.current_repetition + 1},{self.participant_id},{self.input_method},{self.delay},"
            f"{self.width},{self.distance},{self.current_errors},{start_time},{end_time}\n"
        )
        self.log_file.flush()

    # manages transitions to next repetition, condition, etc.
    def handle_transition(self):
        if self.current_repetition < self.repetitions - 1:
            # increment current repetition, reset per-trial trackers
            self.current_repetition += 1
            self.current_errors = 0
            self.trial_start_time = None
            self.pointer_inside = False
            self.game_state = "repetition_complete"
        else:
            if self.current_condition_index < len(self.conditions) - 1:
                # increment current condition, reset trackers
                self.current_condition_index += 1
                self.current_repetition = 0
                self.current_errors = 0
                self.trial_start_time = None
                self.pointer_inside = False
                # close current file, setup new condition and logging
                if self.log_file:
                    self.log_file.close()
                self.setup_condition()
                self.setup_logging()
                self.game_state = "condition_complete"
            else:
                self.game_state = "experiment_done"

    # deadzone logic, taken from pointing_input.py / (same as for Fitts')
    def apply_deadzone(self, val, deadzone):
        val = max(deadzone, min(1 - deadzone, val))
        return (val - deadzone) / (1 - 2 * deadzone)

    # for latency (same as for Fitts')
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

    # push true pointer position into the buffer, update last position (attributes) / (same as for Fitts')
    def update_pointer(self, true_x, true_y):
        now = int(time.time() * 1000)
        self.pointer_buffer.append((now, true_x, true_y))  # push the true position
        self.last_pose_x, self.last_pose_y = self.read_delayed(
            now, true_x, true_y
        )  # read back the delayed position

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
                # go to waiting_start: clock only starts once the pointer reaches the start zone
                self.game_state = "waiting_start"

    # update - called every frame
    def update(self, dt):
        # MOUSE AND TOUCHPAD
        # track cursor position (during waiting_start and trial_running)
        if self.game_state in ("waiting_start", "trial_running") and (
            self.input_method == "mouse" or self.input_method == "touchpad"
        ):
            true_x, true_y = self.window._mouse_x, self.window._mouse_y
            self.update_pointer(
                true_x, true_y
            )  # push new position into buffer each frame

        # POSE
        # (no click handling here, unlike Fitts: steering is position-based)
        if self.input_method == "pose" and self.game_state in (
            "waiting_start",
            "trial_running",
        ):
            frame_ok, frame = self.webcam.read()  # grab camera frame
            if not frame_ok:
                return

            # parse the camera frame
            pointer, annotated_image = self.hand_detector.get_pointer_state(
                frame
            )  # returns a normalized (x,y) pointer, annotated img

            if self.show_camera_feed:
                cv2.imshow(
                    "Pose Debug", annotated_image
                )  # camera feedback if show_camera_feed == True (for tests and debugging mainly)

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

        # WAITING FOR START: arm the clock once the pointer enters the start zone
        if self.game_state == "waiting_start":
            # left edge of the tunnel (start zone is a thin band at the entrance)
            center_x = WINDOW_WIDTH / 2
            center_y = WINDOW_HEIGHT / 2
            tunnel_left = center_x - self.distance / 2
            wall_bottom_y = center_y - self.width / 2
            wall_top_y = center_y + self.width / 2

            in_start_zone = (
                tunnel_left <= self.last_pose_x <= tunnel_left + ZONE_WIDTH
                and wall_bottom_y <= self.last_pose_y <= wall_top_y
            )

            if in_start_zone:
                # pointer entered start zone: start the clock and begin trial
                self.trial_start_time = int(time.time() * 1000)
                self.game_state = "trial_running"

        # TRIAL RUNNING: track wall touches (errors) and detect arrival at the end zone
        elif self.game_state == "trial_running":
            center_x = WINDOW_WIDTH / 2
            center_y = WINDOW_HEIGHT / 2
            tunnel_left = center_x - self.distance / 2
            tunnel_right = center_x + self.distance / 2
            wall_bottom_y = center_y - self.width / 2
            wall_top_y = center_y + self.width / 2

            # check if pointer is inside the tunnel (between both walls, along its length)
            in_tunnel = (
                tunnel_left <= self.last_pose_x <= tunnel_right
                and wall_bottom_y <= self.last_pose_y <= wall_top_y
            )

            if in_tunnel:
                # pointer is (back) inside: mark it so the next exit counts as a new error
                self.pointer_inside = True

                # check if pointer reached the end zone (thin band at the right edge)
                if self.last_pose_x >= tunnel_right - ZONE_WIDTH:
                    # trial complete: log and transition
                    end_time = int(time.time() * 1000)
                    self.log_trial(self.trial_start_time, end_time)
                    self.handle_transition()
            else:
                # pointer is outside tunnel walls
                if self.pointer_inside:
                    # only count as a new error if pointer was inside before (one error per exit, not per frame)
                    self.current_errors += 1
                    self.pointer_inside = False

    # init screen
    def draw_init_screen(self):
        title = pyglet.text.Label(
            "Steering Law Test",
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
            "Guide the pointer through the tunnel\nwithout touching the walls.",
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
            f"Width: {self.width}  |  Distance: {self.distance}",
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

        # errors counter during trial
        pyglet.text.Label(
            f"Errors: {self.current_errors}",
            x=WINDOW_WIDTH // 2,
            y=WINDOW_HEIGHT - 30,
            anchor_x="center",
            anchor_y="center",
            font_size=SMALL_FONT_SIZE,
            color=(*CURRENT_TARGET_COLOR, 255),
        ).draw()

    # draw
    def on_draw(self):
        self.window.clear()

        if self.game_state in ("waiting_start", "trial_running"):
            # draw tunnel (walls + start/end lines)
            self.wall_bottom.draw()
            self.wall_top.draw()
            self.start_line.draw()
            self.end_line.draw()

            # draw pointer dot (delayed red dot, same as Fitts)
            pointer_dot = pyglet.shapes.Circle(
                self.last_pose_x, self.last_pose_y, 10, color=POINTER_COLOR
            )
            pointer_dot.draw()

            self.draw_hud()

            # "Start" label under the left edge of the tunnel
            pyglet.text.Label(
                "Start",
                x=WINDOW_WIDTH / 2 - self.distance / 2,
                y=WINDOW_HEIGHT / 2 - self.width / 2 - WALL_THICKNESS - 15,
                anchor_x="center",
                anchor_y="center",
                font_size=SMALL_FONT_SIZE,
                color=(*COMMANDS_TEXT_COLOR, 255),
            ).draw()

            # "End" label under the right edge of the tunnel
            pyglet.text.Label(
                "End",
                x=WINDOW_WIDTH / 2 + self.distance / 2,
                y=WINDOW_HEIGHT / 2 - self.width / 2 - WALL_THICKNESS - 15,
                anchor_x="center",
                anchor_y="center",
                font_size=SMALL_FONT_SIZE,
                color=(*CURRENT_TARGET_COLOR, 255),
            ).draw()

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