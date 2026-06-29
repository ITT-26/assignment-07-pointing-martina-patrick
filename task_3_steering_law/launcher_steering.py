import argparse
import json
import pyglet

from steering_law import SteeringLawApp, WINDOW_HEIGHT, WINDOW_WIDTH


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
        "-d", "--distance", type=int, help="Tunnel distance"
    )  # tunnel distance
    parser.add_argument("-w", "--width", type=int, help="Tunnel width")  # tunnel width

    args = parser.parse_args()

    # load config
    if args.config:
        steering_config = load_config(args.config)
    else:
        # validate that all required parameters are provided
        required_params = [
            args.participant_id,
            args.repetitions,
            args.input_method,
            args.delay,
            args.distance,
            args.width,
        ]
        if not all(p is not None for p in required_params):
            parser.error(
                "If no config file provided, you must specify: --participant_id, --repetitions, --input_method, --delay, --distance, --width"
            )

        steering_config = {
            "participant_id": args.participant_id,
            "conditions": [
                {
                    "input_method": args.input_method,
                    "delay": args.delay,
                    "width": args.width,
                    "distance": args.distance,
                    "repetitions": args.repetitions,
                }
            ],
        }

    # validate config
    validate_config(steering_config)

    # run app
    app = SteeringLawApp(steering_config)
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
        required_condition_fields = [
            "width",
            "distance",
            "repetitions",
            "input_method",
            "delay",
        ]

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
        if condition["width"] <= 0:
            raise ValueError(
                f"Condition {i}: width must be positive, got: {condition['width']}"
            )
        if condition["distance"] <= 0:
            raise ValueError(
                f"Condition {i}: distance must be positive, got: {condition['distance']}"
            )
        if condition["repetitions"] <= 0:
            raise ValueError(
                f"Condition {i}: repetitions must be positive, got: {condition['repetitions']}"
            )

        # check if tunnel fits on screen
        # distance (rectangle length), takes into account some padding
        if condition["distance"] > WINDOW_WIDTH - 60:
            raise ValueError(
                f"Condition {i}: tunnel doesn't fit on screen. "
                f"Distance ({condition['distance']}) must be <= {WINDOW_WIDTH} - 60"
            )
        # width (space between rectangles), takes into account some padding and also the drawn rectangles' width
        # TODO: change when rectangles are drawn
        if condition["width"] > WINDOW_HEIGHT - 100:
            raise ValueError(
                f"Condition {i}: tunnel doesn't fit on screen. "
                f"Width ({condition['width']}) must be <= {WINDOW_HEIGHT} - 100"
            )


if __name__ == "__main__":
    main()
