import time

import hardware.car as Car
import hardware.ultrasonic as Ultrasonic
from libs import ACB_Canmv
from navigation.track import TrackFollower

# ==================================================
# HARDWARE
# ==================================================
car = Car.Car()
ultrasonic = Ultrasonic.UltrasonicScanner()
cam = ACB_Canmv.ACB_Canmv()
cam.init(cam.SDA, cam.SCL)
time.sleep_ms(500)

track = TrackFollower(car)

# ==================================================
# STATES
# ==================================================
FOLLOW_TRACK = 0
APPROACH_CORNER = 1
TURNING = 2
FIND_TRACK = 3
state = FOLLOW_TRACK

# ==================================================
# SETTINGS
# ==================================================
WALL_DETECT_CM = 40
TURN_TRIGGER_CM = 25
EMERGENCY_CM = 10

CORNER_APPROACH_SPEED = 85
CORNER_TURN_SPEED = 110
TRACK_SEARCH_SPEED = 75
CORNER_EXIT_SPEED = 95

MIN_TURN_TIME_MS = 200   # reduced from 350
MAX_TURN_TIME_MS = 2200
TURN_OPEN_DISTANCE_CM = 20

TRACK_CENTER_TOLERANCE = 8
TRACK_CONFIRMATIONS = 3

TURN_DIRECTION = "left"

ULTRASONIC_INTERVAL_MS = 120
last_ultrasonic_check = time.ticks_ms()
front_distance = 999

lap = 1
corner_count = 0
CORNERS_PER_LAP = 4
track_memory = []
straight_started_ms = time.ticks_ms()

turn_started_ms = 0
track_found_count = 0

# ==================================================
# CAMERA
# ==================================================
def read_track():
    if cam.visual_patrol():
        error = cam.Visual_data
        return True, error
    return False, 0

# ==================================================
# ULTRASONIC
# ==================================================
def update_front_distance():
    global front_distance, last_ultrasonic_check
    now = time.ticks_ms()
    if time.ticks_diff(now, last_ultrasonic_check) >= ULTRASONIC_INTERVAL_MS:
        front_distance = ultrasonic.get_stable_distance()
        last_ultrasonic_check = now
        print("Front:", front_distance, "cm")
    return front_distance

# ==================================================
# CORNER MOVEMENT
# ==================================================
def drive_corner():
    if TURN_DIRECTION == "left":
        car.rotate_left(CORNER_TURN_SPEED)
    else:
        car.rotate_right(CORNER_TURN_SPEED)

def search_corner():
    if TURN_DIRECTION == "left":
        car.rotate_left(TRACK_SEARCH_SPEED)
    else:
        car.rotate_right(TRACK_SEARCH_SPEED)

# ==================================================
# RECORD / FINISH CORNER
# ==================================================
def record_corner():
    global straight_started_ms
    now = time.ticks_ms()
    straight_time = time.ticks_diff(now, straight_started_ms)
    if lap == 1:
        track_memory.append({
            "corner": corner_count + 1,
            "straight_time_ms": straight_time,
            "wall_distance": front_distance
        })
        print("LEARNED CORNER", corner_count + 1,
              "Straight:", straight_time, "ms",
              "Wall:", front_distance, "cm")

def complete_lap():
    global lap
    lap += 1
    print("\n==============================")
    print("LAP", lap - 1, "COMPLETE")
    print("==============================")
    if lap == 2:
        print("Track learned.")
        print("Increasing straight speed.")
        print("Memory:", track_memory)
    print("Starting lap:", lap, "\n")

def finish_corner():
    global corner_count, straight_started_ms, track_found_count, state
    car.stop()
    time.sleep_ms(100)
    car.forward(CORNER_EXIT_SPEED)
    time.sleep_ms(120)
    corner_count += 1
    print("\nCORNER COMPLETE:", corner_count)
    if corner_count >= CORNERS_PER_LAP:
        corner_count = 0
        complete_lap()
    straight_started_ms = time.ticks_ms()
    track_found_count = 0
    state = FOLLOW_TRACK

# ==================================================
# START
# ==================================================
car.stop()
time.sleep_ms(500)
print("\n==============================")
print("MUCHENGETI TRACK NAVIGATION")
print("==============================\n")
print("Camera = primary navigation")
print("Ultrasonic = secondary wall sensor")
print("Turn direction:", TURN_DIRECTION)
print("Lap:", lap, "\n")

# ==================================================
# MAIN LOOP
# ==================================================
while True:
    if state == FOLLOW_TRACK:
        valid_track, error = read_track()
        if valid_track:
            action = track.follow(error, lap)
            print("TRACK Error:", error, "Action:", action, "Lap:", lap)
        else:
            speed = track.learning_speed if lap == 1 else track.fast_speed
            car.forward(speed)
            print("Track temporarily lost")

        distance = update_front_distance()
        if distance <= EMERGENCY_CM:
            print("\nEMERGENCY WALL:", distance)
            print("Forcing corner now")
            record_corner()
            turn_started_ms = time.ticks_ms()
            track_found_count = 0
            drive_corner()
            state = TURNING
            continue
        if distance <= WALL_DETECT_CM:
            print("\nWall approaching:", distance)
            state = APPROACH_CORNER
            continue

    elif state == APPROACH_CORNER:
        valid_track, error = read_track()
        if valid_track:
            if abs(error) <= 5:
                car.forward(CORNER_APPROACH_SPEED)
            elif error < 0:
                car.diagonal_forward_left(80)
            else:
                car.diagonal_forward_right(80)
        else:
            car.forward(CORNER_APPROACH_SPEED)

        distance = update_front_distance()
        print("CORNER APPROACH Distance:", distance)
        if distance <= TURN_TRIGGER_CM:
            print("\n==============================")
            print("START CORNER", TURN_DIRECTION.upper())
            print("Wall:", distance, "cm")
            print("==============================\n")
            record_corner()
            turn_started_ms = time.ticks_ms()
            track_found_count = 0
            drive_corner()
            state = TURNING

    elif state == TURNING:
        now = time.ticks_ms()
        elapsed = time.ticks_diff(now, turn_started_ms)
        if elapsed < MIN_TURN_TIME_MS:
            drive_corner()
            time.sleep_ms(20)
            continue
        if elapsed >= MAX_TURN_TIME_MS:
            print("Main corner phase timeout")
            track_found_count = 0
            state = FIND_TRACK
            continue

        distance = update_front_distance()
        if TURN_DIRECTION == "right" and distance > TURN_OPEN_DISTANCE_CM:
            print("TURN: open space detected:", distance, "cm")
            car.stop()
            time.sleep_ms(100)
            car.forward(CORNER_EXIT_SPEED)
            time.sleep_ms(120)
            track_found_count = 0
            state = FIND_TRACK
            continue

        valid_track, error = read_track()
        if not valid_track:
            print("TURN: track not visible")
            drive_corner()
            track_found_count = 0
            continue

        print("TURN CAMERA Error:", error, "Elapsed:", elapsed)
        if abs(error) <= TRACK_CENTER_TOLERANCE:
            track_found_count += 1
            print("Track alignment:", track_found_count, "/", TRACK_CONFIRMATIONS)
            car.stop()
            time.sleep_ms(100)
            car.forward(CORNER_EXIT_SPEED)
            if track_found_count >= TRACK_CONFIRMATIONS:
                print("New straight acquired")
                finish_corner()
        else:
            track_found_count = 0
            # proportional correction instead of fixed diagonal
            if error < 0:
                car.diagonal_forward_left(CORNER_TURN_SPEED)
            else:
                car.diagonal_forward_right(CORNER_TURN_SPEED)

    elif state == FIND_TRACK:
        search_corner()
        valid_track, error = read_track()
        if not valid_track:
            print("SEARCH: no track")
            time.sleep_ms(20)
            continue
        print("SEARCH TRACK Error:", error)
        if abs(error) <= TRACK_CENTER_TOLERANCE:
            track_found_count += 1
            car.stop()
            time.sleep_ms(100)
            car.forward(CORNER_EXIT_SPEED)
            print("Search alignment:", track_found_count, "/", TRACK_CONFIRMATIONS)
            if track_found_count >= TRACK_CONFIRMATIONS:
                print("Track recovered")
                finish_corner()
        else:
            track_found_count = 0
            search_corner()

    time.sleep_ms(20)