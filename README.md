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


# Task 2, 3 and 4



# Task 5

DISCLAIMER: Usually data/results would not be uploaded via git directly to avoid clutter.
Since we will only have data for 3 participants and the results will not be shared via
other sources we decided to include the results directly in the repo.

## Method

The method can be split into two parts: The theory and what should be done in an ideal 
scenario and then what we actually did in our specific scenario.

### Theory

Optimally, the number of participants would be determined by the experiment setup. 
In our case we have 4 input techniques as conditions, on top of that we have 3 radii and
3 distances for Fitt's Law as well as 3 lengths and 3 widths for steering law. To 
counterbalance this we can use a latin square approach. Using all possible combinations
to do so would result in 4 x 3 x 3 = 36 conditions and would therefore need 36 participants
if we were to counterbalance this with a latin square. 

Another approach is focusing on input device and doing a 4 condition latin square or a
full counterbalancing which would still result in more than 3 participants.

After each input device we would probably design a questionnaire or use an already
existing one to determine how users felt about the device.

### Reality

The reason why counterbalancing is done is to prevent biases like the learning effect or
participants getting tired over time. With only 3 participants this is simply not feasible
which is why we decided on keeping the order of input devices and other conditions the 
same for each participant. This way we can at least say that all participants had the same
conditions and the learning effect, tiredness etc. should be the same for each participant. 
This does still not factor in that people learn at different rates or that some might get
tired faster than others but still sounded like the best approach given this specific 
scenario.

We can use a quesstionnaire, but it will only contain some questions that we consider 
important. We will ask users to rate the following statements on likert scales from 
1 (Strongly disagree) to 7 (strongly agree):
- Using this input method was pleasant
- This input method feels natural and intuitive to use
- I had no problems using this input method

## Procedure

Here some lines about how the study went

## Results

Results go here and will link to a jupyter notebook that I will create

## Discussion

Interpretation of results goes here

## Problems

### Issues with the Method

Since we only had a run with 3 participants it was basically impossible to counterbalance
this study. Apart from that a study with 3 participants (of which 2 designed the study and
therefore has knowledge beforehand) has little value. If at all it would be used to check
for an initial effect or to test the setup like a pilot study.

### Issues with implementation

The hand detector cou use some additional smoothing and maybe some code to reduce jitter
and other smaller problems. However, since the detector works pretty decently for the 
most part this was skipped due to time constraints.