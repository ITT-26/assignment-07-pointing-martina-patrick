from argparse import ArgumentParser

from pointing_input import PointingInput

def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("-c", "--cam", required=False, default=False, type=bool,
                        help="Display camera to user?")
    parser.add_argument("-cd", "--cam-deadzone", required=False, default=.1, type=float)
    args = parser.parse_args()
    camera = args.cam
    dz = args.cam_deadzone
    print(dz)
    if not 0 <= dz < .5:
        dz = .1
        print('Deadzone must be between 0 and .5, defaulting to .1')
    pointing_input = PointingInput(camera_deadzone=dz, camera=camera)
    pointing_input.start()

if __name__ == '__main__':
    main()