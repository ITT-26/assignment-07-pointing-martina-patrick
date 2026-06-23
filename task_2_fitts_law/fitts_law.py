# here goes your Fitts' Law application

import pyglet
import time
import math
import random

# window setup parameters
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 800

# design constants
TARGET_COLOR = (45, 130, 183)  # blue
CURRENT_TARGET_COLOR = (185, 98, 45)  # orange
POINTER_COLOR = (200, 50, 50)  # red
TEXT_COLOR = (255, 255, 255)  # white
BG_COLOR = (40, 40, 40)  # dark gray


class FittsLawApp:
    def __init__(self, config: dict):

        # extract info from config file
        self.participant_id = config["participant_id"]
        self.input_method = config["input_method"]
        self.delay = config["delay"]
        self.conditions = config["conditions"]
        self.multiple_conditions = (
            len(self.conditions) > 1
        )  # not sure if I'm going to use this after all, rev.

        # log file
        self.log_file = None

        # init window
        self.window = pyglet.window.Window(
            width=WINDOW_WIDTH, height=WINDOW_HEIGHT, caption="Fitts' Law"
        )
        # bg color
        pyglet.gl.glClearColor(*[c / 255.0 for c in BG_COLOR], 1.0)
        self.window.on_draw = self.on_draw

        # init state
        self.current_condition_index = 0
        self.current_repetition = 0
        self.current_target_index = 0
        self.game_state = "init_screen"  # "init_screen", "trial_running", "iteration_complete", "condition_complete", "experiment_done"

        # first (or only) condition display setup
        self.setup_condition()
        self.targets[self.sequence[0]]["circle"].color = CURRENT_TARGET_COLOR

        # logging setup
        self.setup_logging()

        # track time for timestamps
        self.trial_start_time = None  # it starts once the user clicks

        # pyglet update loop scheduling
        pyglet.clock.schedule_interval(self.update, 1 / 60.0)

    def setup_condition(self):
        num_targets = self.conditions[self.current_condition_index]["num_targets"]
        radius = self.conditions[self.current_condition_index]["radius"]
        distance = self.conditions[self.current_condition_index]["distance"]
        repetitions = self.conditions[self.current_condition_index]["repetitions"]

        # get center of the window
        center_x = WINDOW_WIDTH / 2
        center_y = WINDOW_HEIGHT / 2

        self.targets = []
        for n in range(num_targets):
            angle = (2 * math.pi * n) / num_targets
            x = center_x + (distance / 2) * math.cos(angle)
            y = center_y + (distance / 2) * math.sin(angle)
            circle = pyglet.shapes.Circle(x, y, radius, color=TARGET_COLOR)
            self.targets.append({"circle": circle, "x": x, "y": y, "index": n})

        # random initial target, pre-compute target order
        start = random.randint(0, num_targets - 1)
        self.sequence = []
        for i in range(num_targets // 2):
            self.sequence.append((start + i) % num_targets)
            self.sequence.append((start + i + num_targets // 2) % num_targets)

    def setup_logging(self):
        condition = self.conditions[self.current_condition_index]
        filename = (
            f"fitts_{self.participant_id}_{self.input_method}_"
            f"{self.delay}ms_{condition['num_targets']}_"
            f"{condition['radius']}_{condition['distance']}.csv"
        )
        self.log_file = open(filename, "w")
        self.log_file.write(
            "iteration,part_id,input_method,delay,num_targets,radius,distance,target_id,timestamp\n"
        )
        self.log_file.flush()

    def on_draw(self):
        self.window.clear()
        for target in self.targets:
            target["circle"].draw()

    def update(self, dt):
        pass


# TODO:
# - handle mouse click events: check if click lands on current target (distance to center <= radius)
# - on successful click: log the trial, advance current_target_index, highlight next target
# - on last target in sequence: increment current_repetition, reset sequence (new random start)
# - on last repetition: if more conditions, close log, setup_condition(), setup_logging(); else game_state = "experiment_done"
# - draw init screen (game_state == "init_screen"), start trial on keypress
# - draw completion screen (game_state == "experiment_done")
# - handle pose input (with Patrick's work)
# - correct paths, folders for results and config
# - test sample config file for continuous run (although this is for Task 5 mainly)
