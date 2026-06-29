import argparse
import json
import pyglet

# use:
#   $env:PYTHONPATH="."; py task_5/launcher_study.py -c task_5/study_config.json -p test -T fitts
#   $env:PYTHONPATH="."; py task_5/launcher_study.py -c task_5/study_config.json -p test -T steering


from task_2_fitts_law.fitts_law import (
    FittsLawApp,
    WINDOW_WIDTH as FITTS_WINDOW_WIDTH,
    WINDOW_HEIGHT as FITTS_WINDOW_HEIGHT,
)

from task_3_steering_law.steering_law import (
    SteeringLawApp,
    WINDOW_WIDTH as STEERING_WINDOW_WIDTH,
    WINDOW_HEIGHT as STEERING_WINDOW_HEIGHT,
)


# loads a json config file - same as task 2 and 3 launchers
def load_config(config_path: str) -> dict:
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found: {config_path}")
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON in config file: {config_path}")


# build the config the apps expect
# now participant id is given as a parameter, and the task can be chosen
def build_config(full_config: dict, participant_id: str, task: str) -> dict:
    if task not in full_config:
        raise ValueError(
            f"Config has no '{task}' block. Found: {list(full_config.keys())}"
        )
    block = full_config[task]
    if "conditions" not in block or not block["conditions"]:
        raise ValueError(f"'{task}' block has no (non-empty) 'conditions'.")
    # assemble the dict
    return {"participant_id": participant_id, "conditions": block["conditions"]}


# NOTE ON VALIDATION: for the study, we don't accept command line parameters anymore; instead we use a pre-made config file
# therefore validation isn't that relevant
# we include it anyways in case the config generator made a mistake


# validates arguments - FITTS - taken from task 2 launcher
def validate_fitts(config: dict) -> None:
    for i, c in enumerate(config["conditions"]):
        required = [
            "num_targets",
            "radius",
            "distance",
            "repetitions",
            "input_method",
            "delay",
        ]
        missing = [f for f in required if f not in c]
        if missing:
            raise ValueError(f"Fitts condition {i} missing fields: {missing}")
        if c["input_method"] not in ("pose", "mouse", "touchpad"):
            raise ValueError(
                f"Fitts condition {i}: bad input_method {c['input_method']}"
            )
        if c["delay"] < 0:
            raise ValueError(f"Fitts condition {i}: delay cannot be negative")
        if c["num_targets"] < 2 or c["num_targets"] > 10:
            raise ValueError(f"Fitts condition {i}: num_targets must be 2-10")
        if c["num_targets"] % 2 != 0:
            raise ValueError(
                f"Fitts condition {i}: num_targets must be EVEN "
                f"(odd values break the target sequence), got {c['num_targets']}"
            )
        if c["radius"] <= 0 or c["distance"] <= 0 or c["repetitions"] <= 0:
            raise ValueError(f"Fitts condition {i}: numeric fields must be positive")
        max_from_center = min(FITTS_WINDOW_WIDTH, FITTS_WINDOW_HEIGHT) / 2
        farthest = c["distance"] / 2 + c["radius"]
        if farthest > max_from_center:
            raise ValueError(
                f"Fitts condition {i}: targets don't fit "
                f"({farthest} > {max_from_center})"
            )


# validates arguments - STEERING - taken from task 3 launcher
def validate_steering(config: dict) -> None:
    for i, c in enumerate(config["conditions"]):
        required = ["width", "distance", "repetitions", "input_method", "delay"]
        missing = [f for f in required if f not in c]
        if missing:
            raise ValueError(f"Steering condition {i} missing fields: {missing}")
        if c["input_method"] not in ("pose", "mouse", "touchpad"):
            raise ValueError(
                f"Steering condition {i}: bad input_method {c['input_method']}"
            )
        if c["delay"] < 0:
            raise ValueError(f"Steering condition {i}: delay cannot be negative")
        if c["width"] <= 0 or c["distance"] <= 0 or c["repetitions"] <= 0:
            raise ValueError(f"Steering condition {i}: numeric fields must be positive")
        if c["distance"] > STEERING_WINDOW_WIDTH - 60:
            raise ValueError(f"Steering condition {i}: tunnel distance off screen")
        if c["width"] > STEERING_WINDOW_HEIGHT - 100:
            raise ValueError(f"Steering condition {i}: tunnel width off screen")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c", "--config", required=True, help="Path to JSON config file"
    )
    parser.add_argument("-p", "--participant_id", required=True, help="Participant ID")
    parser.add_argument(
        "-T",
        "--task",
        required=True,
        choices=["fitts", "steering"],
        help="Which task block to run",
    )
    args = parser.parse_args()

    full_config = load_config(args.config)
    config = build_config(full_config, args.participant_id, args.task)

    if args.task == "fitts":
        validate_fitts(config)
        app = FittsLawApp(config)
    else:
        validate_steering(config)
        app = SteeringLawApp(config)

    pyglet.app.run()


if __name__ == "__main__":
    main()
