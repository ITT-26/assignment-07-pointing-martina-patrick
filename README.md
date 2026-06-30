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
 
All commands assume you run from the project root with the project root on the Python path. 

On PowerShell:
 
```powershell
$env:PYTHONPATH="."
```
 
Both applications share the same structure: a `*_law.py` file with the app class
and an accompanying `launcher_*.py` that handles argument parsing and config
validation.

 Use `[SPACE]` to start and advance
through the screens, and `q` / `[ESC]` to quit at any point.
 
## Task 2
 
### How to use
 
The launcher accepts a JSON config file or individual command line
parameters.
 
With a config file:
 
```powershell
$env:PYTHONPATH="."; py task_2_fitts_law/launcher_fitts.py -c task_2_fitts_law/example_config_fitts.json
```
 
With individual parameters (together they represent one "condition"):
 
```powershell
$env:PYTHONPATH="."; py task_2_fitts_law/launcher_fitts.py -p test -n 2 -i mouse -l 0 -d 300 -r 50 -t 6
```
 
| Flag | Meaning |
|------|---------|
| `-p` / `--participant_id` | Participant ID |
| `-n` / `--repetitions` | Repetitions per condition |
| `-i` / `--input_method` | `pose`, `mouse` or `touchpad` |
| `-l` / `--delay` | Latency in ms (`0` to disable, see Task 4) |
| `-d` / `--distance` | Distance between opposing targets (diameter of the target ring) |
| `-r` / `--radius` | Target radius |
| `-t` / `--num_targets` | Number of targets (even, 2–10) |
 
A config file holds a `participant_id` and a list of `conditions`, so several
conditions can be run back to back in a single session without closing the
window. 
 
The launcher validates the config before launching: `num_targets` must be even
and between 2 and 10, all numeric fields must be positive, and the targets must
fit on screen (`distance / 2 + radius <= min(width, height) / 2`).

### Implementation
 
The `num_targets` targets are placed evenly around a ring centred in the window;
`distance` is the ring's diameter, so it equals the spacing between two
diametrically opposed targets. At the start of each repetition a random target is
chosen and the full click sequence is precomputed, alternating across the ring
(target `i` paired with target `i + num_targets/2`). The active target is highlighted in orange.
 
The app is a small state machine: `init_screen` → `condition_complete` →
`trial_running` → `repetition_complete` (and on to the next condition or
`experiment_done`). Mouse and touchpad register a click on left mouse press; pose
input moves the OS cursor via `pynput` from the MediaPipe hand landmarks and fires
a click on the pinch gesture described in Task 1.
 
Hit detection is evaluated against a displayed red dot position, not the raw event coordinates. This matters because that
dot can be a delayed position (Task 4), so the check stays consistent across all
input methods and latency conditions.
 
### What is logged and where
 
One CSV file is written per condition to:
 
```
task_2_fitts_law/results/fitts_<part_id>_<input_method>_<delay>ms_<num_targets>_<radius>_<distance>.csv
```
 
One row is logged **per click** (hit or miss). Header:
 
```
iteration,part_id,input_method,delay,num_targets,radius,distance,target_id,hit,timestamp
```
 
`hit` is `1` for a hit and `0` for a miss, and `timestamp` is an absolute Unix timestamp in milliseconds.


## Task 3
 
### How to use
 
Same pattern as Task 2: config file or individual parameters.
 
With a config file:
 
```powershell
$env:PYTHONPATH="."; py task_3_steering_law/launcher_steering.py -c task_3_steering_law/example_config_steering.json
```
 
With individual parameters:
 
```powershell
$env:PYTHONPATH="."; py task_3_steering_law/launcher_steering.py -p test -n 2 -i mouse -l 0 -d 300 -w 50
```
 
The flags are identical to Task 2, except for the two task-specific ones:
 
| Flag | Meaning |
|------|---------|
| `-d` / `--distance` | Tunnel length (horizontal) |
| `-w` / `--width` | Tunnel width (vertical gap between the walls) |
 
There is no more `num_targets`, and `width` replaces `radius`.
 
Validation requires all numeric fields to be positive and the tunnel to fit on
screen (`distance <= width - 60`, `width <= height - 100`).
 
### Implementation
 
The setup is a horizontal corridor centred in the window: two blue walls a gap of
`width` apart, spanning a length of `distance`. A green start line marks the left
entrance and an orange end line marks the right exit.
 
There is an extra state compared to Fitts', `waiting_start`: after `[SPACE]` the
tunnel is drawn but the clock is not running. The timer starts only when the
pointer enters the start zone and stops when it
reaches the end zone. Because steering is
position-based, there is no clicking involved for any input method.
 
Errors are wall touches. The app tracks whether the pointer was inside the tunnel
on the previous frame, so leaving the corridor counts as one error per exit
rather than one per frame. 
 
### What is logged and where
 
One CSV file is written per condition to:
 
```
task_3_steering_law/results/steering_<part_id>_<input_method>_<delay>ms_<width>_<distance>.csv
```
 
One row is logged per completed tunnel (one repetition). Header:
 
```
iteration,part_id,input_method,delay,width,distance,errors,start_time,end_time
```
 
`errors` is the number of wall exits during that run, and `start_time` /
`end_time` are absolute Unix timestamps in milliseconds.

# Task 4
 
Latency is controlled by the `delay` parameter (milliseconds), which is part of every condition and always has to be specified. Setting delay to `0` disables it.
 
The delay path is identical in both applications and is encapsulated in two
methods, `update_pointer()` and `read_delayed()`.
 
A position buffer stores recent pointer samples
as `(timestamp_ms, x, y)`. 
Every frame, `update_pointer()` pushes the true pointer position with a Unix-ms
timestamp and then calls `read_delayed()` to read back the position the pointer
held `delay` ms ago. That read-back position is what is drawn (the red dot) and
what hit/steering detection uses.
 
`read_delayed()` computes a single target time, `now - self.delay`, and returns a
sample for it:
 
- empty buffer (first frame): return the current true coordinates;
- target older than the oldest buffered sample: return the oldest sample;
- otherwise: find the two samples that bracket the target time and return the nearer of the two.
 
The decision to make the buffer interpolate between discrete frames was made because exact matches are
unlikely: pyglet schedules at ~60 fps (~16.7 ms per frame, and not even evenly in
practice), 150 ms is not a multiple of that, and `now` is rounded to whole
milliseconds. This also means that the true latency is not exactly what is stated as a parameter.

The buffer is cleared at the
start of every trial so stale samples from a previous trial cannot leak into the
timing of the next one.


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

- how did we acquire participants
- how we explained the task
- etc

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