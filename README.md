[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/KfEU5Azw)

# Venv

We are using Python 3.14 for this assignment. It is recommended to create a 
venv for this project

# Task 1

Use task_1/launcher.py to start the application. The command line takes 2 
optional arguments. -c or --cam which should be set to True or False and 
determines if opencv should display what the camera sees (recommended for debugging 
purposes) and -cd or --cam-deadzone which should be a float between 0 and .5 and
adds a deadzone to the edges of the camera where the mediapipe detection starts to
jitter increasingly. I find that .2 seems to be an acceptable value for now.

Starting the application allows you to control the cursor with the tip of the index
finger, pinching the thumb tip and middle finger tip will simulate a click (
detection not 100% guaranteed, can behave wonky
)

Q can be used to quit but only when using -c True, otherwise you can use Ctrl-C. 
If no hand is detected the cursor will be controlled by the mouse as is usual