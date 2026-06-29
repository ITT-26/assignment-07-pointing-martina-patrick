# config generator for task 5 trials

import json
import random

SEED = 42  # fixed seed to reproduce rand
ITERATIONS = 3  # at least 3
NUM_TARGETS = 8  # fixed target number across all fitts conditions

INPUT_DEVICES = [
    # input, delay[ms]
    ("mouse", 0),
    ("mouse", 150),
    ("touchpad", 0),
    ("pose", 0),  # user goes through all conditions with one input method, then moves on to the next input method
                  # if it was random we would have to open and close the webcam several times
]

# chosen distances and radii for fitts law test
FITTS_DISTANCES = [350, 450, 550]
FITTS_RADII = [25, 40, 55]

# chosen distances and widths for steering law test
STEERING_DISTANCES = [400, 600, 800]
STEERING_WIDTHS = [60, 100, 140]

# resulting config file path
CONFIG_FILE_PATH = "study_config.json"


# config for fitts
def fitts_conditions(rng):
    conditions = []
    for input_method, delay in INPUT_DEVICES:
        grid = []
        for d in FITTS_DISTANCES:
            for r in FITTS_RADII:
                grid.append((d, r))  # store all combinations
        rng.shuffle(grid)  # vary order
        for distance, radius in grid:
            conditions.append(
                {
                    "input_method": input_method,
                    "delay": delay,
                    "num_targets": NUM_TARGETS,
                    "radius": radius,
                    "distance": distance,
                    "repetitions": ITERATIONS,
                }
            )
    return conditions

# config for steering
def steering_conditions(rng):
    conditions = []
    for input_method, delay in INPUT_DEVICES:
        grid = []
        for d in STEERING_DISTANCES:
            for r in STEERING_WIDTHS:
                grid.append((d, r))
        rng.shuffle(grid)  # difficulty order variation
        for distance, width in grid:
            conditions.append(
                {
                    "input_method": input_method,
                    "delay": delay,
                    "width": width,
                    "distance": distance,
                    "repetitions": ITERATIONS,
                }
            )
    return conditions


def main():
    rng = random.Random(SEED)
    config = {
        "fitts": {"conditions": fitts_conditions(rng)},
        "steering": {"conditions": steering_conditions(rng)},
    }

    with open(CONFIG_FILE_PATH, "w") as f:
        json.dump(config, f, indent=2)


if __name__ == "__main__":
    main()
