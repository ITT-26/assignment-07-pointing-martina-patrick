import argparse
import json
import pyglet

from fitts_law import FittsLawApp, WINDOW_HEIGHT, WINDOW_WIDTH


# the user can either provide the path to a config file or the individual parameters
def main() -> None:
    parser = argparse.ArgumentParser()
    # json config file
    parser.add_argument("-c", "--config", type=str, help="Path to JSON config file")

    # parameters - required if no config file is provided
    parser.add_argument(
        "-p", "--participant_id", type=str, help="Participant ID"
    )  # participant id
    parser.add_argument(
        "-n", "--repetitions", type=int, help="Number of repetitions per condition"
    )  # number of repetitions
    parser.add_argument(
        "-i", "--input_method", type=str, help="Input method: pose, mouse, touchpad"
    )  # input method - pose, mouse, touchpad
    parser.add_argument("-l", "--delay", type=int, help="Latency in ms")  # latency
    parser.add_argument(
        "-d", "--distance", type=int, help="Distance between targets"
    )  # distance between targets (diameter of the circle that contains the targets - because in a 2-target display, this would be the distance between targets)
    parser.add_argument(
        "-r", "--radius", type=int, help="Target radius"
    )  # target radius
    parser.add_argument(
        "-t", "--num_targets", type=int, help="Number of targets (between 2 and 10)"
    )  # number of targets

    args = parser.parse_args()

    # load config
    if args.config:
        fitts_config = load_config(args.config)
    else:
        # validate that all required parameters are provided
        required_params = [
            args.participant_id,
            args.repetitions,
            args.input_method,
            args.delay,
            args.distance,
            args.radius,
            args.num_targets,
        ]
        if not all(p is not None for p in required_params):
            parser.error(
                "If no config file provided, you must specify: --participant_id, --repetitions, --input_method, --delay, --distance, --radius, --num_targets"
            )

        fitts_config = {
            "participant_id": args.participant_id,
            "conditions": [
                {
                    "input_method": args.input_method,
                    "delay": args.delay,
                    "num_targets": args.num_targets,
                    "radius": args.radius,
                    "distance": args.distance,
                    "repetitions": args.repetitions,
                }
            ],
        }

    # validate config
    validate_config(fitts_config)

    # run app
    app = FittsLawApp(fitts_config)
    pyglet.app.run()


# loads a json config file
def load_config(config_path: str) -> dict:
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found: {config_path}")
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON in config file: {config_path}")


# validates parsed arguments
def validate_config(config: dict) -> None:

    required_top_level = ["participant_id", "conditions"]

    # check all required fields exist
    missing = [field for field in required_top_level if field not in config]
    if missing:
        raise ValueError(f"Config missing required fields: {missing}")

    # validate conditions list
    if not config["conditions"] or not isinstance(config["conditions"], list):
        raise ValueError("conditions must be a non-empty list")

    for i, condition in enumerate(config["conditions"]):
        required_condition_fields = ["num_targets", "radius", "distance", "repetitions", "input_method", "delay"]

        missing_condition = [
            field for field in required_condition_fields if field not in condition
        ]
        if missing_condition:
            raise ValueError(f"Condition {i} missing fields: {missing_condition}")
        
        # validate input_method
        valid_methods = ["pose", "mouse", "touchpad"]
        if condition["input_method"] not in valid_methods:
            raise ValueError(
                f"Condition {i}: input_method must be one of {valid_methods}, got: {condition['input_method']}"
            )

        # validate delay
        if condition["delay"] < 0:
            raise ValueError(f"Condition {i}: delay cannot be negative")

        # validate numeric fields in each condition
        if condition["num_targets"] < 2 or condition["num_targets"] > 10:
            raise ValueError(
                f"Condition {i}: num_targets must be between 2 and 10, got: {condition['num_targets']}"
            )
        if condition["radius"] <= 0:
            raise ValueError(
                f"Condition {i}: radius must be positive, got: {condition['radius']}"
            )
        if condition["distance"] <= 0:
            raise ValueError(
                f"Condition {i}: distance must be positive, got: {condition['distance']}"
            )
        if condition["repetitions"] <= 0:
            raise ValueError(
                f"Condition {i}: repetitions must be positive, got: {condition['repetitions']}"
            )

        # check if targets fit on screen
        MAX_DISTANCE_FROM_CENTER = min(WINDOW_WIDTH, WINDOW_HEIGHT) / 2

        farthest_point = condition["distance"]/2 + condition["radius"]
        if farthest_point > MAX_DISTANCE_FROM_CENTER:
            raise ValueError(
                f"Condition {i}: targets don't fit on screen. "
                f"distance ({condition['distance']}) + radius ({condition['radius']}) = {farthest_point} "
                f"must be <= {MAX_DISTANCE_FROM_CENTER}"
            )


if __name__ == "__main__":
    main()
