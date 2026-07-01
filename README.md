[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/KfEU5Azw)

# Setup

## Patrick
I used Python 3.14 and the requirements-patrick.txt modules. Everything worked this way
(at least on my machine ;))

```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows
pip install -r requirements-patrick.txt
```

## Martina
I used Python 3.13.2 and the requirements-martina.txt modules. 

```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows
pip install -r requirements-martina.txt
```

# Task 1

Use `task_1/launcher.py` to start the application. The command line takes 2 
optional arguments: `-c` or `--cam`. which should be set to True or False and 
determines if opencv should display what the camera sees (recommended for debugging 
purposes) and `-cd` or `--cam-deadzone`, which should be a float between 0 and .5 and
adds a deadzone to the edges of the camera where the mediapipe detection starts to
jitter increasingly. We found that .2 seems to be an acceptable value for now.

Starting the application allows you to control the cursor with the tip of the index
finger, pinching the thumb tip and middle finger tip will simulate a left click (detection not 100% guaranteed, can behave wonky, specially under bad lighting conditions).

`q` can be used to quit but only when using `-c True`, otherwise you can use `[Ctrl] + C`. 
If no hand is detected the cursor will be controlled by the mouse/touchpad as is usual.


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
| `-o` / `--output_dir` | Output directory for result CSVs (default: `task_2_fitts_law/data`) |
 
> The `-o` / `--output_dir` flag works in both modes (config file or individual parameters) and lets you save results to a different directory. If used together with `-c` and the config file also specifies `output_dir`, the command-line flag takes precedence.

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
3 distances for Fitts' Law as well as 3 lengths and 3 widths for steering law. To 
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

We can use a questionnaire, but it will only contain some questions that we consider 
important. We will ask users to rate the following statements on likert scales from 
1 (Strongly disagree) to 7 (strongly agree):
- Using this input method was pleasant
- This input method felt natural and intuitive to use
- I had no problems using this input method

## Participants

Three participants took part: the two of us, plus one person outside the ITT
course. Participants were free to use either hand for the pose condition and
could switch hands between repetitions.

## Procedure

1. Conditions were pre-generated with a fixed random seed. For Fitts' Law we
   tested 3 target distances (350, 450, 550 px) and 3 target radii (25, 40,
   55 px), with the number of targets fixed at 8; for Steering Law we tested
   3 tunnel distances (400, 600, 800 px) and 3 tunnel widths (60, 100, 140
   px). Crossing these gives 9 distance/radius (or distance/width)
   combinations per task, times 4 input device blocks (mouse, mouse + 150ms
   delay, touchpad, pose) = 36 distinct conditions per task. In terms of
   index of difficulty (ID = log2(D/W + 1) for Fitts, with W = 2 x radius;
   ID = D/W for Steering), this covers roughly 2.1-3.6 bits for Fitts and
   2.9-13.3 for Steering. Each condition was repeated 3 times in a row,
   giving 108 trials per task and 216 per participant in total.
2. Participants were briefed on both tasks and given time to try each input
   method beforehand, especially pose input, which was new to everyone.
3. Fitts' Law was run first, then Steering Law, in the same fixed order for
   all participants (see Method for why we did not counterbalance).
4. Each task had to be started manually per device block: launching the
   corresponding application with the right parameters, explaining the task
   to the participant, and assisting them as needed.
5. During pose conditions, the webcam feed was kept visible so participants
   could see what the hand detector was tracking.
6. Participants could take breaks between conditions or repetitions.
7. Two of the three participants used the same computer; the third used their
   own laptop (see Problems).
8. After both tasks, participants filled out the short feedback questionnaire
   described in Method.

## Results

Raw per-trial data for all three participants is available in the
[`data`](task_5/data) folder (one CSV per condition). The plots referenced
below are saved as PDFs in [`task_5/results`](task_5/results).

We tested 4 input methods - mouse, mouse with delay (latency), hand detection and touchpad -
by using a Fitts' Law and a Steering Law test.

### Fitts

It can be seen that the throughput ([`fitts_tp.pdf`](task_5/results/fitts_tp.pdf))
of the mouse is the best of all tested input methods. Mouse with delay
performs a bit worse but still manages to beat the touchpad. The hand as
an input device performed worse than the rest. The mouse+delay shows the
least variance of all tested methods.

In terms of accuracy ([`fitts_ac.pdf`](task_5/results/fitts_ac.pdf)) for
Fitts' Law all input methods performed well, showing a high mean accuracy and
a low variance. The only outlier here is the hand, which has a mean accuracy
of only 70% and a high variance.

Breaking down throughput and movement time by index of difficulty
([`fitts_tp_by_id.pdf`](task_5/results/fitts_tp_by_id.pdf),
[`fitts_mt_by_id.pdf`](task_5/results/fitts_mt_by_id.pdf)), the same ranking
observed above (mouse > mouse+delay ≈ touchpad > pose) holds across the whole
difficulty range tested (ID ≈ 2.1-3.6 bits). Movement time for mouse,
mouse+delay and touchpad increases roughly linearly with ID; pose increases
more steeply and with more noise, including a marked jump at the highest ID
tested.

Accuracy by difficulty ([`fitts_acc_by_id.pdf`](task_5/results/fitts_acc_by_id.pdf))
shows mouse, mouse+delay and touchpad staying consistently above 90%
regardless of ID, while pose fluctuates between 58% and 91% without a clear
trend against ID.

### Steering

Completion time ([`steering_ct.pdf`](task_5/results/steering_ct.pdf)) by
input method shows mouse as the fastest method with the tightest spread,
followed by mouse+delay and touchpad, which overlap considerably with
each other. Pose is the slowest method and also shows the widest spread.

Error rate ([`steering_err.pdf`](task_5/results/steering_err.pdf)) by input
method shows mouse with the lowest error rate and least variance. Mouse with
delay, touchpad and pose all show higher and more variable error rates, with
no single method standing out as clearly worse the way pose did for
completion time.

Movement time and throughput by difficulty
([`steering_mt_by_id.pdf`](task_5/results/steering_mt_by_id.pdf),
[`steering_tp_by_id.pdf`](task_5/results/steering_tp_by_id.pdf)) follow the
same ranking as above: mouse fastest / highest throughput, followed by
touchpad and mouse+delay overlapping and crossing each other, and pose
consistently slowest / lowest throughput. Movement time for all methods
increases with ID.

Error rate by difficulty ([`steering_err_by_id.pdf`](task_5/results/steering_err_by_id.pdf))
is noisier than the other two metrics: no input method shows a consistently
low or high error rate across the whole ID range, though touchpad and pose
reach the highest error rates at high difficulty, while mouse stays at or
near 0% for most of the range.

## Discussion

### Fitts

We can safely say that the hand detection performed worst of all methods.
One theory for this is that while participants are usually used to a mouse or
touchpad, using the finger as pointer and touching the thumb and middle finger
for a click is an approach not many people have seen yet. Another factor is the 
quality of the hand detection. Since the detection does not work perfectly it
can very well happen for clicks to be registered on accident, for one click to 
turn into multiples, for a click to be not registered or for the pointer to jitter 
and jump around right before the click, causing the user to miss the target.

Users will probably have no muscle memory when using their hand and will therefore 
have to move slower and adjust their pointer more often, causing a significant 
decrease in throughput. 

These factors could all lead to the hand detection performing quite worse when
compared to all the other input methods. 

The touchpads throughput may be less when compared to the mouse since lifting 
the finger and tapping costs time at every click.

Even though the delay of 150ms led to worse results it was still above the touchpad.
It can be argued that muscle memory does not suffer from delay and the only factor 
leading to a decreased throughput is users waiting for the pointer to arrive
at the target before actually clicking. That takes potentially less time than the
fingerlifting, tapping and repositioning the touchpad requires.

Looking at the difficulty breakdown, the gap between input methods does not
noticeably shrink at low difficulty or grow at high difficulty, but pose remains
clearly worse across the entire range tested. This suggests the performance
gap is driven more by fundamental differences between the input methods than by
how demanding a specific condition is. The fluctuation in
pose accuracy points in the same direction: it looks more consistent with
detector reliability issues (see Problems) than with task difficulty.

### Steering

As with Fitts, pose performed worst overall. Having taken part in the study
ourselves, we can say that detection noise/jitter is likely the main reason
the hand-tracked pointer touched the tunnel walls more often than a mouse or
touchpad would.

Touchpad and mouse+delay perform similarly to each other and worse than plain
mouse. For mouse+delay, the constant
150ms lag likely forces users to move more cautiously to avoid overshooting
into the walls, which costs time and, unlike Fitts, does not fully protect
against errors. For touchpad, the smaller sensing surface can sometimes make it harder to hold a
precise straight path through narrower tunnels.

Error rate did not show as clean a separation between methods as completion
time did. This is likely partly a measurement limitation: error rate only
counts discrete wall-exit events per trial, so with just 3 participants and 3
repetitions per condition, a single unlucky wall touch can swing the rate
considerably for a given condition.

## Feedback Survey

After completing both tasks, participants rated each input method using a
survey (see Method/Procedure). Results can be seen in ([`feedback_survey.pdf`](task_5/results/feedback_survey.pdf)). Note: the third participant is recorded as "AAM112321" in the PDF file (we don't know why, he wrote down 'hector' originally).

Mouse (no delay) scored highest or tied-highest on all three statements,
including a unanimous top rating on "I had no problems using this input
method". This was not surprising, given it is by far the most familiar input method of
the four.

Touchpad and mouse+delay scored similarly to each other, roughly in the
middle across all three statements. 

Pose scored clearly lowest on "pleasant" and "no problems". However, it did not score dramatically worse on "felt natural and
intuitive to use". Hadn't 2 out of 3 participants of the study been the ones who designed the gesture, getting this result in a larger study could suggest 
that pose input weaker performance stems more from hand detection
reliability and precision than from the underlying interaction concept.

## Problems

### Issues with the Method

Since we only had a run with 3 participants it was basically impossible to counterbalance
this study. Apart from that a study with 3 participants (of which 2 designed the study and
therefore have knowledge beforehand) has little value. If at all it would be used to check
for an initial effect or to test the setup like a pilot study.

### Issues with Procedure

One participant used their own laptop for the study and not the same machine that was used
by the two other participants. This means that a different screen resolution,
refresh rate and many other factors could influence and skew the results. This is 
insanely bad practice, but since this is not a real study that will be published
we decided it was okay (since otherwise there would have not been any time to recruit
a third participant). In addition to using another device this person also used 
software that shares a mouse between Computers (specifically "Mouse without Borders"
provided by the Windows PowerToys suite). This can of course also greatly affect
the way the mouse behaved in the experiment.

Running through all 72 conditions with their repetitions (36 for Fitts, 36 for Steering, 3 repetitions each) per
participant made for a fairly long session. Even with breaks allowed between
conditions, participants got visibly more tired as the session went on, which
likely affected performance in the later conditions regardless of input method
or difficulty level, on top of the learning effect discussed above.

Lighting conditions in the room were not controlled or kept consistent across
sessions, and pose-based hand detection is known to be sensitive to lighting.
Some of the accuracy differences we observed for the pose condition may
therefore be partly attributable to lighting rather than to the input method
itself.

### Issues with Implementation

The hand detector could use some additional smoothing and maybe some code to reduce jitter
and other smaller problems. However, since the detector works pretty decently for the 
most part this was skipped due to time constraints.

Additionally, none of the three launchers support pausing or resuming a
session: if a run is interrupted unexpectedly (like a crash, or the
participant needing an extended break), there is no way to continue from a
specific condition, the whole task has to be restarted from the beginning.

# Disclaimer - AI Usage

AI was used to assist plot generation and to help write parts of this README file (based on our own appreciations and conclusions).