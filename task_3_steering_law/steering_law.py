# here goes your Steering Law application

import pyglet
import time
import pathlib
import cv2
import ctypes
from mediapipe.tasks.python import vision
from pynput.mouse import Controller

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
START_ZONE_WIDTH = 20


class SteeringLawApp:
    def __init__(self, config: dict):

        # extract info from config file
        self.participant_id = config["participant_id"]
        self.conditions = config["conditions"]

        # log file
        self.log_file = None

        # state trackers
        self.current_condition_index = 0
        self.current_repetition = 0
        self.current_errors = 0
        self.trial_start_time = None
        self.pointer_inside = False
        self.game_state = "init_screen"  # "init_screen", "trial_running", "repetition_complete", "condition_complete", "experiment_done"

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
            width=WINDOW_WIDTH, height=WINDOW_HEIGHT, caption="Steering's Law"
        )

        user32 = ctypes.windll.user32
        self.screen_width = user32.GetSystemMetrics(0)
        self.screen_height = user32.GetSystemMetrics(1)

        # bg color
        pyglet.gl.glClearColor(*[c / 255.0 for c in BG_COLOR], 1.0)

        # callbacks
        self.window.on_draw = self.on_draw
        # self.window.on_mouse_press = self.on_mouse_press
        self.window.on_key_press = self.on_key_press

        # pose detection setup
        self.hand_detector = None
        self.webcam = None
        self.show_camera_feed = True  # True for debugging, False for app, LABEL_DEBUG
        self.cam_deadzone = 0.1

        # first (or only) condition setup
        self.setup_condition()  # here the current condition's condition-specific parameters are updated

        # pyglet update loop scheduling
        pyglet.clock.schedule_interval(self.update, 1 / 60.0)

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
            self.cleanup_camera()

        # tunnel geometry
        center_x = WINDOW_WIDTH / 2
        center_y = WINDOW_HEIGHT / 2

        tunnel_left = center_x - self.distance / 2
        tunnel_right = center_x + self.distance / 2
        wall_bottom_y = center_y - self.width / 2
        wall_top_y = center_y + self.width / 2

        # walls
        self.wall_bottom = pyglet.shapes.Rectangle(
            x=tunnel_left,
            y=wall_bottom_y - WALL_THICKNESS,
            width=self.distance,
            height=WALL_THICKNESS,
            color=TARGET_COLOR,
        )
        self.wall_top = pyglet.shapes.Rectangle(
            x=tunnel_left,
            y=wall_top_y,
            width=self.distance,
            height=WALL_THICKNESS,
            color=TARGET_COLOR,
        )

        # start and end lines
        self.start_line = pyglet.shapes.Line(
            tunnel_left,
            wall_bottom_y,
            tunnel_left,
            wall_top_y,
            thickness=2,
            color=COMMANDS_TEXT_COLOR,
        )
        self.end_line = pyglet.shapes.Line(
            tunnel_right,
            wall_bottom_y,
            tunnel_right,
            wall_top_y,
            thickness=2,
            color=CURRENT_TARGET_COLOR,
        )

    def setup_logging(self):
        pathlib.Path("task_3_steering_law/results").mkdir(parents=True, exist_ok=True)
        filename = (
            f"task_3_steering_law/results/steering_{self.participant_id}_{self.input_method}_"
            f"{self.delay}ms_{self.width}_{self.distance}.csv"
        )
        self.log_file = open(filename, "w")
        self.log_file.write(
            "iteration,part_id,input_method,delay,width,distance,errors,start_time,end_time\n"
        )
        self.log_file.flush()

    def log_trial(self, start_time, end_time):
        self.log_file.write(
            f"{self.current_repetition + 1},{self.participant_id},{self.input_method},{self.delay},"
            f"{self.width},{self.distance},{self.current_errors},{start_time},{end_time}\n"
        )
        self.log_file.flush()

    def handle_transition(self):
        if self.current_repetition < self.repetitions - 1:
            self.current_repetition += 1
            self.current_errors = 0
            self.trial_start_time = None
            self.pointer_inside = False
            self.game_state = "repetition_complete"
        else:
            if self.current_condition_index < len(self.conditions) - 1:
                self.current_condition_index += 1
                self.current_repetition = 0
                self.current_errors = 0
                self.trial_start_time = None
                self.pointer_inside = False
                if self.log_file:
                    self.log_file.close()
                self.setup_condition()
                self.setup_logging()
                self.game_state = "condition_complete"
            else:
                self.game_state = "experiment_done"

    def apply_deadzone(self, val, deadzone):
        val = max(deadzone, min(1 - deadzone, val))
        return (val - deadzone) / (1 - 2 * deadzone)

    def on_key_press(self, symbol, modifiers):
        if symbol == pyglet.window.key.Q or symbol == pyglet.window.key.ESCAPE:
            self.cleanup()
            pyglet.app.exit()
        elif symbol == pyglet.window.key.SPACE:
            if self.game_state == "init_screen":
                self.game_state = "condition_complete"
            elif self.game_state in ("repetition_complete", "condition_complete"):
                if self.game_state == "condition_complete":
                    self.setup_condition()
                    self.setup_logging()
                self.game_state = "waiting_start"

    def update(self, dt):
        # track cursor position for mouse/touchpad
        if self.game_state in ("waiting_start", "trial_running") and (
            self.input_method == "mouse" or self.input_method == "touchpad"
        ):
            self.last_pose_x = self.window._mouse_x
            self.last_pose_y = self.window._mouse_y

        # track cursor position for pose
        if self.input_method == "pose" and self.game_state in (
            "waiting_start",
            "trial_running",
        ):
            frame_ok, frame = self.webcam.read()
            if not frame_ok:
                return

            pointer, annotated_image = self.hand_detector.get_pointer_state(frame)

            if self.show_camera_feed:
                cv2.imshow("Pose Debug", annotated_image)

            if pointer == Pointer.invalid_pointer():
                return

            norm_x = self.apply_deadzone(pointer.x, self.cam_deadzone)
            norm_y = self.apply_deadzone(pointer.y, self.cam_deadzone)

            cursor_x = norm_x * self.screen_width
            cursor_y = norm_y * self.screen_height

            if not hasattr(self, "pose_mouse"):
                self.pose_mouse = Controller()

            self.pose_mouse.position = (cursor_x, cursor_y)

            # lock red dot to window-relative cursor position
            self.last_pose_x = self.window._mouse_x
            self.last_pose_y = self.window._mouse_y

        if self.game_state == "waiting_start":
            # check if pointer entered the start zone (left edge of tunnel)
            center_x = WINDOW_WIDTH / 2
            center_y = WINDOW_HEIGHT / 2
            tunnel_left = center_x - self.distance / 2
            wall_bottom_y = center_y - self.width / 2
            wall_top_y = center_y + self.width / 2

            in_start_zone = (
                tunnel_left <= self.last_pose_x <= tunnel_left + START_ZONE_WIDTH
                and wall_bottom_y <= self.last_pose_y <= wall_top_y
            )

            if in_start_zone:
                # pointer entered start zone: start the clock and begin trial
                self.trial_start_time = int(time.time() * 1000)
                self.game_state = "trial_running"

        elif self.game_state == "trial_running":
            center_x = WINDOW_WIDTH / 2
            center_y = WINDOW_HEIGHT / 2
            tunnel_left = center_x - self.distance / 2
            tunnel_right = center_x + self.distance / 2
            wall_bottom_y = center_y - self.width / 2
            wall_top_y = center_y + self.width / 2

            # check if pointer is inside the tunnel
            in_tunnel = (
                tunnel_left <= self.last_pose_x <= tunnel_right
                and wall_bottom_y <= self.last_pose_y <= wall_top_y
            )

            if in_tunnel:
                # pointer is back inside after an error: reset flag
                self.pointer_inside = True

                # check if pointer reached the end zone
                if self.last_pose_x >= tunnel_right - START_ZONE_WIDTH:
                    # trial complete: log and transition
                    end_time = int(time.time() * 1000)
                    self.log_trial(self.trial_start_time, end_time)
                    self.handle_transition()
            else:
                # pointer is outside tunnel walls
                if self.pointer_inside:
                    # only count as new error if pointer was inside before
                    self.current_errors += 1
                    self.pointer_inside = False

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

        pyglet.text.Label(
            f"Participant ID: {self.participant_id}",
            x=WINDOW_WIDTH // 2,
            y=300,
            anchor_x="center",
            anchor_y="center",
            font_size=INFO_FONT_SIZE,
            color=(*BODY_TEXT_COLOR, 255),
        ).draw()

        pyglet.text.Label(
            "[SPACE]: start/continue | 'q' / [ESC]: quit",
            x=WINDOW_WIDTH // 2,
            y=100,
            anchor_x="center",
            anchor_y="center",
            font_size=INFO_FONT_SIZE,
            color=(*COMMANDS_TEXT_COLOR, 255),
        ).draw()

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

    def draw_condition_screen(self):
        pyglet.text.Label(
            f"Condition {self.current_condition_index + 1} of {len(self.conditions)}:",
            x=WINDOW_WIDTH // 2,
            y=WINDOW_HEIGHT // 2 + 250,
            anchor_x="center",
            anchor_y="center",
            font_size=LARGE_FONT_SIZE,
            color=(*BODY_TEXT_COLOR, 255),
        ).draw()

        pyglet.text.Label(
            f"Input: {self.input_method}",
            x=WINDOW_WIDTH // 2,
            y=WINDOW_HEIGHT // 2 + 150,
            anchor_x="center",
            anchor_y="center",
            font_size=SUBTITLE_FONT_SIZE - 2,
            color=TARGET_COLOR,
        ).draw()

        pyglet.text.Label(
            f"Delay: {self.delay} ms",
            x=WINDOW_WIDTH // 2,
            y=WINDOW_HEIGHT // 2 + 80,
            anchor_x="center",
            anchor_y="center",
            font_size=INFO_FONT_SIZE,
            color=(*BODY_TEXT_COLOR, 255),
        ).draw()

        pyglet.text.Label(
            f"Width: {self.width}  |  Distance: {self.distance}",
            x=WINDOW_WIDTH // 2,
            y=WINDOW_HEIGHT // 2 + 20,
            anchor_x="center",
            anchor_y="center",
            font_size=INFO_FONT_SIZE,
            color=(*BODY_TEXT_COLOR, 255),
        ).draw()

        pyglet.text.Label(
            f"You will need to repeat this task {self.repetitions} times.",
            x=WINDOW_WIDTH // 2,
            y=WINDOW_HEIGHT // 2 - 100,
            anchor_x="center",
            anchor_y="center",
            font_size=INFO_FONT_SIZE,
            color=BODY_TEXT_COLOR,
        ).draw()

        pyglet.text.Label(
            "Press [SPACE] to start",
            x=WINDOW_WIDTH // 2,
            y=100,
            anchor_x="center",
            anchor_y="center",
            font_size=INFO_FONT_SIZE,
            color=(*COMMANDS_TEXT_COLOR, 255),
        ).draw()

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

    def draw_hud(self):
        pyglet.text.Label(
            f"Rep: {self.current_repetition + 1}/{self.repetitions}",
            x=WINDOW_WIDTH - 10,
            y=WINDOW_HEIGHT - 30,
            anchor_x="right",
            anchor_y="center",
            font_size=SMALL_FONT_SIZE,
            color=(*BODY_TEXT_COLOR, 255),
        ).draw()

        pyglet.text.Label(
            f"Condition: {self.current_condition_index + 1}/{len(self.conditions)}",
            x=10,
            y=WINDOW_HEIGHT - 30,
            anchor_x="left",
            anchor_y="center",
            font_size=SMALL_FONT_SIZE,
            color=(*BODY_TEXT_COLOR, 255),
        ).draw()

        pyglet.text.Label(
            f"Input method: {self.input_method}",
            x=WINDOW_WIDTH // 2,
            y=30,
            anchor_x="center",
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

    def on_draw(self):
        self.window.clear()

        if self.game_state in ("waiting_start", "trial_running"):
            # draw tunnel
            self.wall_bottom.draw()
            self.wall_top.draw()
            self.start_line.draw()
            self.end_line.draw()

            # draw pointer dot
            pointer_dot = pyglet.shapes.Circle(
                self.last_pose_x, self.last_pose_y, 10, color=POINTER_COLOR
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

    def cleanup_camera(self):
        if self.webcam:
            self.webcam.release()
            self.webcam = None
        if self.show_camera_feed:
            try:
                cv2.destroyWindow("Pose Debug")
            except cv2.error:
                pass

    def cleanup(self):
        self.cleanup_camera()
        if self.log_file:
            self.log_file.close()
