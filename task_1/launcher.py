from argparse import ArgumentParser

from pointing_input import PointingInput

def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("-c", "--cam", required=False, default=False, type=bool,
                        help="Display camera to user?")
    args = parser.parse_args()
    camera = args.cam
    pointing_input = PointingInput(camera=camera)
    pointing_input.start()

if __name__ == '__main__':
    main()