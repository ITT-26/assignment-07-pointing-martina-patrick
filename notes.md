# Task 1

## Mappings

Index finger moves pointer

Thumb + Middle finger --> Click

## Structure

OpenCV for camera capture and display

main.py -> Captures camera, handles clicks and moves

hand_detector.py -> returns a dict with new pointer position and 
True/False for click

## Logic 
main captures frame, sends frame to detector 

detector finds hand and saves x and y pos of index. detector checks if ring finger
tip and thumb tip collide (are close enough) and sets click to true

{x: x_coord, y: y_coord, click: True/False} (Can be expanded to include left_click
and right_click if need be)

Maybe build in a memory system to not fire repeated clicks

main moves the pointer using pynput and simulates a click if click is True


# Task 2 + 3

## Structure

Copy the hand_detector from Task 1 

Create a launcher.py that reads out arguments from the command line and passes them
to a class that runs a pyglet app

main.py the pyglet application

hand_detector from before


## Logic

launcher reads config and passes it to pyglet. 

main.py sets up the first experiment run, displays targets and activates the 
correct input method

if the user uses hand input we use our hand_detector again

the next setup is loaded. Every setup is repeated 3 times

# Splitting work

| Patrick        | Martina                     |
|----------------|-----------------------------|
| Task 1         | Pyglet part of Task 2 and 3 |
| Hand detector  | ------------                |
| Config loading | ------------                |
