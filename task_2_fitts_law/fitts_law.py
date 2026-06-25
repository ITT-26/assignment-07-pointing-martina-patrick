# here goes your Fitts' Law application

import pyglet
import time
import math
import random
import pathlib

# window setup parameters
WINDOW_WIDTH = 800
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


class FittsLawApp:
    def __init__(self, config: dict):

        # extract info from config file
        self.participant_id = config["participant_id"]
        self.conditions = config["conditions"]

        # log file
        self.log_file = None

        # init window
        self.window = pyglet.window.Window(
            width=WINDOW_WIDTH, height=WINDOW_HEIGHT, caption="Fitts' Law"
        )
        # bg color
        pyglet.gl.glClearColor(*[c / 255.0 for c in BG_COLOR], 1.0)
        # callbacks
        self.window.on_draw = self.on_draw
        self.window.on_mouse_press = self.on_mouse_press
        self.window.on_key_press = self.on_key_press

        # init state
        self.current_condition_index = 0
        self.current_repetition = 0
        self.current_target_index = 0
        self.game_state = "init_screen"  # "init_screen", "trial_running", "repetition_complete", "condition_complete", "experiment_done"

        # condition-specific parameters
        self.input_method = None
        self.delay = None
        self.num_targets = None
        self.radius = None
        self.distance = None
        self.repetitions = None

        # first (or only) condition setup
        self.setup_condition()  # here the current condition's condition-specific parameters are updated

        # track time for timestamps
        self.trial_start_time = None  # it starts once the user clicks

        # pyglet update loop scheduling
        pyglet.clock.schedule_interval(self.update, 1 / 60.0)

    def random_start(self):
        num_targets = self.conditions[self.current_condition_index]["num_targets"]
        start = random.randint(0, num_targets - 1)
        self.sequence = []
        for i in range(num_targets // 2):
            self.sequence.append((start + i) % num_targets)
            self.sequence.append((start + i + num_targets // 2) % num_targets)

    def setup_condition(self):
        self.input_method = self.conditions[self.current_condition_index]["input_method"]
        self.delay = self.conditions[self.current_condition_index]["delay"]
        self.num_targets = self.conditions[self.current_condition_index]["num_targets"]
        self.radius = self.conditions[self.current_condition_index]["radius"]
        self.distance = self.conditions[self.current_condition_index]["distance"]
        self.repetitions = self.conditions[self.current_condition_index]["repetitions"]

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

    def setup_logging(self):
        pathlib.Path("results").mkdir(exist_ok=True)
        filename = (
            f"results/fitts_{self.participant_id}_{self.input_method}_"
            f"{self.delay}ms_{self.num_targets}_"
            f"{self.radius}_{self.distance}.csv"
        )
        self.log_file = open(filename, "w")
        self.log_file.write(
            "iteration,part_id,input_method,delay,num_targets,radius,distance,target_id,timestamp\n"
        )
        self.log_file.flush()

    def log(self, target_id):
        condition = self.conditions[self.current_condition_index]
        timestamp = int((time.time() - self.trial_start_time) * 1000)
        self.log_file.write(
            f"{self.current_repetition},{self.participant_id},{self.input_method},{self.delay},"
            f"{self.num_targets},{self.radius},{self.distance},"
            f"{target_id},{timestamp}\n"
        )
        self.log_file.flush()

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

    def update_visuals(self, old_target):
        old_target["circle"].color = TARGET_COLOR
        if self.game_state == "trial_running":
            self.targets[self.sequence[self.current_target_index]][
                "circle"
            ].color = CURRENT_TARGET_COLOR

    def handle_click(self, x, y):
        # we only care about the target at the current index
        # we want to check whether x, y are inside target_x +- radius, target_y +- radius
        current_target = self.targets[self.sequence[self.current_target_index]]
        distance = math.sqrt(
            (x - current_target["x"]) ** 2 + (y - current_target["y"]) ** 2
        )
        if distance <= self.radius:
            # log
            target_id = current_target["index"]
            self.log(target_id)
            old_target = self.targets[self.sequence[self.current_target_index]]
            # handle transition to next target/end of repetition or condition
            self.handle_transition()
            # update screen
            self.update_visuals(old_target)

    def on_mouse_press(self, x, y, button, modifiers):
        if self.game_state == "trial_running":
            if self.input_method == "mouse" or self.input_method == "touchpad":
                if button == pyglet.window.mouse.LEFT:
                    self.handle_click(x, y)

            # elif self.input_method == "pose":
            #     pass
            #     # si la funcion de Patrick devuelve True para el click
            #     # self.handle_click(x,y)

    def on_key_press(self, symbol, modifiers):
        if symbol == pyglet.window.key.Q or symbol == pyglet.window.key.ESCAPE:
            pyglet.app.exit()
        elif symbol == pyglet.window.key.SPACE:
            if self.game_state == "init_screen":
                self.game_state = "condition_complete"
            elif self.game_state in ("repetition_complete", "condition_complete"):
                if self.game_state == "condition_complete":
                    self.setup_condition()
                    self.setup_logging()
                self.random_start()
                self.targets[self.sequence[0]]["circle"].color = CURRENT_TARGET_COLOR
                self.game_state = "trial_running"
                self.trial_start_time = time.time()

    def draw_init_screen(self):
        # title
        title = pyglet.text.Label(
            "Fitts' Law Test",
            x=WINDOW_WIDTH // 2,
            y=WINDOW_HEIGHT // 2 + 200,
            anchor_x="center",
            anchor_y="center",
            font_size=TITLE_FONT_SIZE,
            color=(*BODY_TEXT_COLOR, 255)
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

        # repetitions (separate emphasis also)
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
            x=WINDOW_WIDTH // 2,
            y=30,
            anchor_x="center",
            anchor_y="center",
            font_size=SMALL_FONT_SIZE,
            color=(*BODY_TEXT_COLOR, 255),
        ).draw()

    def on_draw(self):
        self.window.clear()
        if self.game_state == "trial_running":
            for target in self.targets:
                target["circle"].draw()
            self.draw_hud()
        elif self.game_state == "init_screen":
            self.draw_init_screen()
        elif self.game_state == "repetition_complete":
            self.draw_rep_complete_screen()
        elif self.game_state == "condition_complete":
            self.draw_condition_screen()
        elif self.game_state == "experiment_done":
            self.draw_exp_done_screen()

    def update(self, dt):
        pass


# TODO:

# CHANGE LOG AND CONFIG (PATRICK'S SUGGESTION DS)

# - handle pose input (with Patrick's work)
# - correct paths, folders for results and config
# - if number of targets is low, maybe dont stop the rep after all have been clicked, instead make some extra cycles
