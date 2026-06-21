import argparse
import configparser

from task_2_fitts_law.fitts_law import FittsLawApp


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('-p' '--partid', type=int, required=True) # Participant ID
    parser.add_argument('-d', '--distance', type=int, required=True) # Distance between targets
    parser.add_argument('-s', '--size', type=int, required=True) # Size of targets
    parser.add_argument('-t', '--targets', type=int, required=True) # Number of targets
    parser.add_argument('-c', '--config', type=str, required=False) # Config file for fitts law

    args = parser.parse_args()

    config = args.config
    if config is None:
        fitts_config = {
            'id': args.partid,
            'distance': args.distance,
            'size': args.size,
            'targets': args.targets
        }
    else:
        fitts_config = load_config(config)

    app = FittsLawApp(fitts_config)

def load_config(config_path: str) -> dict:
    # Load the config file
    raise NotImplementedError

if __name__ == '__main__':
    main()