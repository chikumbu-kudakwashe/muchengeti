"""
Muchengeti autonomous navigation.

Current objectives:

1. Stay stationary for the first ten seconds.
2. Detect BLUE or ORANGE to choose the course direction.
3. Run the straight sections at maximum motor command.
4. Detect RED and GREEN traffic pillars.
5. Pass RED on the right.
6. Pass GREEN on the left.
7. Treat a close object with no traffic colour as a wall.
8. Count only real 90-degree track turns.
9. Four turns make one lap.
10. Stop after twelve turns / three laps near the starting point.

Parking will be added as the next phase.
"""

import time

import config.settings as settings

import hardware.car as Car
import hardware.ultrasonic as Ultrasonic

from libs import ACB_Canmv

from navigation.startup import StartupDirectionDetector
from navigation.traffic import TrafficColorDetector
from navigation.track import TrackFollower


# ============================================================
# HARDWARE
# ============================================================

car = Car.Car()

ultrasonic = Ultrasonic.UltrasonicScanner()

cam = ACB_Canmv.ACB_Canmv()

cam.init(
    cam.SDA,
    cam.SCL
)


# ============================================================
# NAVIGATION STATES
# ============================================================

DRIVING = 0

TRAFFIC_APPROACH = 1
TRAFFIC_SHIFT = 2
TRAFFIC_PASS = 3
TRAFFIC_RECENTER = 4

CORNER_APPROACH = 5
CORNER_TURNING = 6
CORNER_TRIM = 10
CORNER_RECOVERY = 7

FINISH_RETURN = 8
FINISHED = 9

state = DRIVING


# ============================================================
# STARTUP DETECTOR
# ============================================================

startup_detector = StartupDirectionDetector(
    camera=cam,

    blue_index=settings.BLUE_INDEX,
    orange_index=settings.ORANGE_INDEX,

    pixels_threshold=(
        settings.START_COLOR_PIXELS_THRESHOLD
    ),

    area_threshold=(
        settings.START_COLOR_AREA_THRESHOLD
    ),

    min_width=(
        settings.START_COLOR_MIN_WIDTH
    ),

    min_height=(
        settings.START_COLOR_MIN_HEIGHT
    ),

    min_area=(
        settings.START_COLOR_MIN_AREA
    ),

    min_votes=(
        settings.START_COLOR_MIN_VOTES
    ),

    vote_margin=(
        settings.START_COLOR_VOTE_MARGIN
    ),

    scan_ms=(
        settings.STARTUP_SCAN_MS
    ),

    sample_delay_ms=(
        settings.STARTUP_SAMPLE_DELAY_MS
    )
)


# ============================================================
# TRAFFIC DETECTOR
# ============================================================

track_follower = TrackFollower(car)

traffic_detector = TrafficColorDetector(
    cam=cam,

    red_index=settings.RED_INDEX,
    green_index=settings.GREEN_INDEX,

    pixels_threshold=(
        settings.TRAFFIC_PIXELS_THRESHOLD
    ),

    area_threshold=(
        settings.TRAFFIC_AREA_THRESHOLD
    ),

    min_width=(
        settings.TRAFFIC_MIN_WIDTH
    ),

    min_height=(
        settings.TRAFFIC_MIN_HEIGHT
    ),

    min_area=(
        settings.TRAFFIC_MIN_AREA
    ),

    confirmations=(
        settings.TRAFFIC_CONFIRMATIONS
    )
)


# ============================================================
# RACE STATE
# ============================================================

course_direction = (
    settings.DEFAULT_TURN_DIRECTION
)

total_turns = 0

race_complete = False


# ============================================================
# ULTRASONIC STATE
# ============================================================

front_distance = 999

last_ultrasonic_ms = (
    time.ticks_ms()
)


# ============================================================
# CORNER STATE
# ============================================================

active_corner_direction = None

# Consecutive close-range frames with no traffic colour detected.
# Used to require several bad reads before committing to a wall.
wall_no_color_streak = 0

turn_started_ms = 0

turn_saw_close_wall = False

corner_trim_started_ms = 0

corner_recovery_started_ms = 0


# ============================================================
# TRAFFIC STATE
# ============================================================

active_traffic_color = None

active_traffic_direction = None

active_traffic_cx = settings.TRAFFIC_CAMERA_CENTER_X

active_traffic_shift_ms = settings.TRAFFIC_SHIFT_MS_MIN

traffic_shift_started_ms = 0

traffic_pass_started_ms = 0

traffic_recenter_started_ms = 0

traffic_recenter_phase = 0

traffic_centered_since_ms = 0

traffic_lost_count = 0

last_traffic_scan_ms = 0

last_traffic_completed_ms = (
    time.ticks_ms()
)


# ============================================================
# FINISH POSITION LEARNING
# ============================================================

run_started_ms = 0

straight_started_ms = 0

first_partial_straight_ms = None

clean_straight_samples = []

traffic_seen_on_current_straight = False

finish_started_ms = 0

finish_drive_ms = (
    settings.FINISH_FORWARD_FALLBACK_MS
)


# ============================================================
# DISTANCE HELPERS
# ============================================================

def is_valid_distance(distance: float) -> bool:
    """
    Check whether an ultrasonic value can be trusted.

    Args:
        distance: Distance returned by the ultrasonic sensor.

    Returns:
        True for a usable distance reading.
    """

    if distance is None:
        return False

    if distance <= 0:
        return False

    if distance >= settings.MAX_VALID_DISTANCE_CM:
        return False

    return True


def update_front_distance() -> float:
    """
    Refresh the front ultrasonic reading at a controlled rate.

    Invalid readings are replaced with 999 rather than keeping an
    old close distance that could trigger another false corner.

    Returns:
        Current front distance in centimetres.
    """

    global front_distance
    global last_ultrasonic_ms

    now = time.ticks_ms()

    if time.ticks_diff(
        now,
        last_ultrasonic_ms
    ) < settings.ULTRASONIC_INTERVAL_MS:

        return front_distance


    distance = (
        ultrasonic.get_stable_distance()
    )


    if is_valid_distance(distance):

        front_distance = distance

    else:

        front_distance = 999


    last_ultrasonic_ms = now

    return front_distance


def read_track() -> tuple:
    """
    Read the camera's line-following error.

    Used only to confirm/steer back to track center after a traffic
    pillar manoeuvre - normal straight-line driving is otherwise
    open-loop and relies on the ultrasonic for corner timing.

    Returns:
        (True, error) if the camera has a usable line reading.
        (False, 0) otherwise.
    """

    if cam.visual_patrol():

        return True, cam.Visual_data

    return False, 0


# ============================================================
# TRAFFIC HELPERS
# ============================================================

def scan_traffic_sign() -> object:
    """
    Check the camera for a red or green traffic pillar.

    Returns:
        Traffic-sign dictionary or None.
    """

    result = traffic_detector.detect()

    if result is None:
        return None


    print(
        "TRAFFIC:",
        result["color"].upper(),
        "PASS:",
        result["direction"].upper(),
        "W:",
        result["width"],
        "H:",
        result["height"],
        "AREA:",
        result["area"]
    )

    return result


def compute_shift_ms(cx: int) -> int:
    """
    Size the sideways avoidance shift to how off-center a pillar is.

    A pillar close to the camera's center line is likely already
    close to the outer wall or the center obstacle and needs a
    smaller sideways move; one far off-center needs more clearance.
    Scales linearly between TRAFFIC_SHIFT_MS_MIN and _MAX using the
    blob's horizontal camera position (getCX).

    Args:
        cx: Horizontal camera position of the pillar blob.

    Returns:
        Shift duration in milliseconds.
    """

    offset = abs(
        cx - settings.TRAFFIC_CAMERA_CENTER_X
    )

    fraction = (
        offset
        /
        settings.TRAFFIC_CX_FULL_OFFSET_PX
    )

    if fraction > 1:
        fraction = 1

    return int(
        settings.TRAFFIC_SHIFT_MS_MIN
        +
        fraction
        *
        (
            settings.TRAFFIC_SHIFT_MS_MAX
            -
            settings.TRAFFIC_SHIFT_MS_MIN
        )
    )


def shift_away_from_pillar(direction: str) -> None:
    """
    Move sideways to the correct side of a traffic pillar.

    Red gives direction='right'.
    Green gives direction='left'.

    Args:
        direction: Side on which the pillar must be passed.

    Returns:
        None.
    """

    if direction == "right":

        car.strafe_right(
            settings.TRAFFIC_SHIFT_SPEED
        )

    else:

        car.strafe_left(
            settings.TRAFFIC_SHIFT_SPEED
        )


def shift_back_to_route(direction: str) -> None:
    """
    Undo the sideways movement used to pass a pillar.

    Args:
        direction: Original traffic-passing direction.

    Returns:
        None.
    """

    if direction == "right":

        car.strafe_left(
            settings.TRAFFIC_RECENTER_SPEED
        )

    else:

        car.strafe_right(
            settings.TRAFFIC_RECENTER_SPEED
        )


# ============================================================
# CORNER HELPERS
# ============================================================

def drive_corner(direction: str, speed: int = None) -> None:
    """
    Pivot the car in place through a 90-degree track turn.

    The ultrasonic is fixed facing forward, so rotating in place
    sweeps it away from the old wall and toward the new straight.
    The CORNER_TURNING state watches that sweep to decide when the
    turn is done.

    Args:
        direction: "left" or "right".
        speed: Rotation speed. Defaults to CORNER_TURN_SPEED.

    Returns:
        None.
    """

    if speed is None:
        speed = settings.CORNER_TURN_SPEED

    if direction == "left":

        car.rotate_left(
            speed
        )

    else:

        car.rotate_right(
            speed
        )


def current_lap() -> int:
    """
    Return the lap currently being driven.

    Returns:
        Lap number from 1 to 3.
    """

    lap = (
        total_turns
        // settings.TURNS_PER_LAP
    ) + 1

    if lap > settings.TOTAL_LAPS:
        lap = settings.TOTAL_LAPS

    return lap


def record_straight_before_corner() -> None:
    """
    Record straight-section timing for finish-position estimation.

    The first measurement is the distance in time from the starting
    position to the first corner. Later clean straight sections give
    us an estimate of a complete straight.

    Straights containing a traffic avoidance manoeuvre are ignored
    because the sideways movement changes their elapsed time.

    Returns:
        None.
    """

    global first_partial_straight_ms

    now = time.ticks_ms()

    elapsed = time.ticks_diff(
        now,
        straight_started_ms
    )


    if total_turns == 0:

        if first_partial_straight_ms is None:

            first_partial_straight_ms = elapsed

            print(
                "START OFFSET LEARNED:",
                first_partial_straight_ms,
                "ms"
            )

        return


    if traffic_seen_on_current_straight:

        print(
            "STRAIGHT TIMING IGNORED - TRAFFIC MANOEUVRE"
        )

        return


    if elapsed < 200:

        return


    clean_straight_samples.append(
        elapsed
    )


    # Keep the most recent values only.
    if len(clean_straight_samples) > 8:

        clean_straight_samples.pop(0)


    print(
        "CLEAN STRAIGHT:",
        elapsed,
        "ms"
    )


def median(values: list) -> int:
    """
    Return the median integer from a list.

    Args:
        values: Numeric values.

    Returns:
        Median value or zero for an empty list.
    """

    if not values:
        return 0

    ordered = list(values)

    ordered.sort()

    count = len(ordered)

    middle = count // 2

    if count % 2 == 1:

        return ordered[middle]


    return (
        ordered[middle - 1]
        +
        ordered[middle]
    ) // 2


def estimate_finish_drive_time() -> int:
    """
    Estimate how far to drive after the twelfth corner.

    After turn 12 we are back on the straight containing the original
    start. A learned full-straight time minus the original start-to-
    first-corner time gives an approximate corner-to-start time.

    Returns:
        Forward-driving time in milliseconds.
    """

    if first_partial_straight_ms is None:

        return settings.FINISH_FORWARD_FALLBACK_MS


    full_straight_ms = median(
        clean_straight_samples
    )


    if full_straight_ms <= 0:

        return settings.FINISH_FORWARD_FALLBACK_MS


    estimate = (
        full_straight_ms
        -
        first_partial_straight_ms
    )


    if estimate < 0:

        estimate = 0


    if estimate > settings.FINISH_FORWARD_MAX_MS:

        estimate = (
            settings.FINISH_FORWARD_MAX_MS
        )


    return estimate


def count_completed_corner() -> None:
    """
    Count one completed physical 90-degree track corner.

    This is the only function that changes total_turns. Traffic
    manoeuvres never call this function.

    Returns:
        None.
    """

    global total_turns

    total_turns += 1


    turn_in_lap = (
        (total_turns - 1)
        %
        settings.TURNS_PER_LAP
    ) + 1


    lap_number = (
        (total_turns - 1)
        //
        settings.TURNS_PER_LAP
    ) + 1


    print("")
    print("================================")

    print(
        "90 DEGREE TURN COMPLETE"
    )

    print(
        "TOTAL:",
        total_turns,
        "/",
        settings.TOTAL_TURNS
    )

    print(
        "LAP:",
        lap_number,
        "TURN:",
        turn_in_lap,
        "/",
        settings.TURNS_PER_LAP
    )


    if (
        total_turns
        %
        settings.TURNS_PER_LAP
        ==
        0
    ):

        print(
            "LAP",
            lap_number,
            "COMPLETE"
        )


    print("================================")
    print("")


# ============================================================
# STARTUP
# ============================================================

car.stop()

print("")
print("================================")
print("MUCHENGETI")
print("WRO AUTONOMOUS NAVIGATION")
print("================================")

print(
    "Zimbabwe field:",
    settings.MAT_SIZE_CM,
    "cm x",
    settings.MAT_SIZE_CM,
    "cm"
)

print(
    "Race target:",
    settings.TOTAL_LAPS,
    "laps /",
    settings.TOTAL_TURNS,
    "corners"
)

print("")


# ============================================================
# 10 SECOND BLUE / ORANGE SCAN
# ============================================================

course_direction = (
    startup_detector.detect(
        settings.DEFAULT_TURN_DIRECTION
    )
)

settings.DEFAULT_TURN_DIRECTION = (
    course_direction
)


print("")
print("================================")
print(
    "COURSE LOCKED:",
    course_direction.upper()
)
print("================================")
print("")

time.sleep_ms(500)


# ============================================================
# BEGIN RACE
# ============================================================

run_started_ms = (
    time.ticks_ms()
)

straight_started_ms = (
    run_started_ms
)


# ============================================================
# MAIN LOOP
# ============================================================

while True:

    now = time.ticks_ms()


    # ========================================================
    # FINISHED
    # ========================================================

    if state == FINISHED:

        car.stop()

        print("")
        print("================================")
        print("RACE COMPLETE")
        print(
            settings.TOTAL_LAPS,
            "LAPS COMPLETE"
        )
        print(
            settings.TOTAL_TURNS,
            "TRACK TURNS COMPLETE"
        )
        print("CAR STOPPED")
        print("================================")
        print("")

        break


    # ========================================================
    # NORMAL DRIVING
    # ========================================================

    if state == DRIVING:

        # Time Attack straight.
        car.forward(
            settings.DRIVE_SPEED
        )


        distance = update_front_distance()


        # ----------------------------------------------------
        # Periodic traffic scan.
        #
        # We scan even when the ultrasonic does not see a close
        # object because a pillar may not be exactly in the centre
        # of the ultrasonic beam.
        # ----------------------------------------------------

        traffic_cooldown_finished = (
            time.ticks_diff(
                now,
                last_traffic_completed_ms
            )
            >=
            settings.TRAFFIC_COOLDOWN_MS
        )


        if (
            traffic_cooldown_finished
            and
            time.ticks_diff(
                now,
                last_traffic_scan_ms
            )
            >=
            settings.TRAFFIC_SCAN_INTERVAL_MS
        ):

            last_traffic_scan_ms = now

            traffic = (
                scan_traffic_sign()
            )


            if traffic is not None:

                active_traffic_color = (
                    traffic["color"]
                )

                active_traffic_direction = (
                    traffic["direction"]
                )

                active_traffic_cx = (
                    traffic["cx"]
                )

                traffic_seen_on_current_straight = True


                print("")
                print(
                    "PILLAR LOCKED:",
                    active_traffic_color.upper()
                )

                print(
                    "PASS:",
                    active_traffic_direction.upper()
                )

                print("")


                state = TRAFFIC_APPROACH

                continue


        # ----------------------------------------------------
        # Something is getting close.
        #
        # Do not hit a wall at full speed while the K210 spends
        # time switching between red and green recognition.
        # ----------------------------------------------------

        if (
            is_valid_distance(distance)
            and
            distance
            <=
            settings.BOUNDARY_CLASSIFY_CM
        ):

            car.forward(
                settings.CLASSIFICATION_SPEED
            )


            # One final traffic check decides whether the close
            # object is a pillar or the track wall.
            traffic = (
                scan_traffic_sign()
            )


            if traffic is not None:

                active_traffic_color = (
                    traffic["color"]
                )

                active_traffic_direction = (
                    traffic["direction"]
                )

                active_traffic_cx = (
                    traffic["cx"]
                )

                traffic_seen_on_current_straight = True

                wall_no_color_streak = 0

                state = TRAFFIC_APPROACH

                continue


            # No red or green on this frame.
            #
            # A single missed read is not enough evidence to commit
            # to an irreversible 90 degree turn - this mat can have
            # a pillar sitting right where a corner would also be
            # expected, so require several consecutive bad reads
            # before treating it as the boundary wall.
            wall_no_color_streak += 1

            if wall_no_color_streak < settings.WALL_CONFIRM_COUNT:

                continue


            wall_no_color_streak = 0

            active_corner_direction = (
                course_direction
            )

            print("")
            print(
                "WALL DETECTED:",
                distance,
                "cm"
            )

            print(
                "CORNER:",
                active_corner_direction.upper()
            )

            state = CORNER_APPROACH

            continue


        else:

            # Nothing close enough to classify - any earlier bad
            # reads no longer apply to whatever we encounter next.
            wall_no_color_streak = 0


        # ----------------------------------------------------
        # Emergency protection.
        # ----------------------------------------------------

        if (
            is_valid_distance(distance)
            and
            distance <= settings.EMERGENCY_CM
        ):

            print(
                "EMERGENCY DISTANCE:",
                distance
            )

            car.backward(
                settings.BACKUP_SPEED
            )

            time.sleep_ms(180)

            car.stop()

            time.sleep_ms(50)

            continue


    # ========================================================
    # TRAFFIC APPROACH
    # ========================================================

    elif state == TRAFFIC_APPROACH:

        car.forward(
            settings.TRAFFIC_APPROACH_SPEED
        )


        distance = update_front_distance()


        if (
            is_valid_distance(distance)
            and
            distance
            <=
            settings.TRAFFIC_PASS_TRIGGER_CM
        ):

            print("")
            print(
                active_traffic_color.upper(),
                "PILLAR ->",
                active_traffic_direction.upper()
            )
            print("")


            # Refresh the pillar's camera position right before the
            # shift - it is now close and large, so this reading is
            # more reliable than the one taken at the original
            # classification distance.
            traffic = scan_traffic_sign()

            if (
                traffic is not None
                and
                traffic["color"] == active_traffic_color
            ):

                active_traffic_cx = traffic["cx"]

            active_traffic_shift_ms = compute_shift_ms(
                active_traffic_cx
            )

            print(
                "SHIFT SIZE:",
                active_traffic_shift_ms,
                "ms"
            )


            traffic_shift_started_ms = (
                time.ticks_ms()
            )


            shift_away_from_pillar(
                active_traffic_direction
            )


            state = TRAFFIC_SHIFT

            continue


    # ========================================================
    # TRAFFIC SIDE SHIFT
    # ========================================================

    elif state == TRAFFIC_SHIFT:

        shift_away_from_pillar(
            active_traffic_direction
        )


        elapsed = time.ticks_diff(
            now,
            traffic_shift_started_ms
        )


        if elapsed >= active_traffic_shift_ms:

            car.forward(
                settings.TRAFFIC_PASS_SPEED
            )


            traffic_pass_started_ms = (
                time.ticks_ms()
            )

            traffic_lost_count = 0

            state = TRAFFIC_PASS

            continue


    # ========================================================
    # PASS TRAFFIC PILLAR
    # ========================================================

    elif state == TRAFFIC_PASS:

        car.forward(
            settings.TRAFFIC_PASS_SPEED
        )


        elapsed = time.ticks_diff(
            now,
            traffic_pass_started_ms
        )


        if elapsed >= settings.TRAFFIC_MIN_PASS_MS:

            traffic = (
                scan_traffic_sign()
            )


            if (
                traffic is not None
                and
                traffic["color"]
                ==
                active_traffic_color
            ):

                traffic_lost_count = 0


            else:

                traffic_lost_count += 1


            if (
                traffic_lost_count
                >=
                settings.TRAFFIC_LOST_CONFIRMATIONS
            ):

                print(
                    "PILLAR CLEARED -> RECENTER"
                )


                traffic_recenter_started_ms = (
                    time.ticks_ms()
                )

                traffic_recenter_phase = 0


                shift_back_to_route(
                    active_traffic_direction
                )


                state = TRAFFIC_RECENTER

                continue


        if elapsed >= settings.TRAFFIC_MAX_PASS_MS:

            print(
                "PILLAR PASS TIMEOUT -> RECENTER"
            )


            traffic_recenter_started_ms = (
                time.ticks_ms()
            )

            traffic_recenter_phase = 0


            shift_back_to_route(
                active_traffic_direction
            )


            state = TRAFFIC_RECENTER

            continue


    # ========================================================
    # RETURN TO ROUTE AFTER PILLAR
    # ========================================================

    elif state == TRAFFIC_RECENTER:

        elapsed = time.ticks_diff(
            now,
            traffic_recenter_started_ms
        )


        # ----------------------------------------------------
        # Phase 0:
        # undo the sideways shift.
        # ----------------------------------------------------

        if traffic_recenter_phase == 0:

            shift_back_to_route(
                active_traffic_direction
            )


            if elapsed >= active_traffic_shift_ms:

                traffic_recenter_phase = 1

                traffic_recenter_started_ms = (
                    time.ticks_ms()
                )


                car.forward(
                    settings.CORNER_EXIT_SPEED
                )

                traffic_centered_since_ms = 0


        # ----------------------------------------------------
        # Phase 1:
        # the timed shift only gets us roughly back in line, so use
        # the camera's track error to steer back to actual center
        # instead of just driving forward for a fixed time.
        # ----------------------------------------------------

        else:

            valid_track, error = read_track()


            if valid_track:

                action = track_follower.follow(
                    error,
                    current_lap()
                )

            else:

                # No usable line reading yet - keep the car moving
                # straight rather than stalling mid-manoeuvre.
                car.forward(
                    settings.CORNER_EXIT_SPEED
                )

                action = None


            if action == "straight":

                if traffic_centered_since_ms == 0:

                    traffic_centered_since_ms = (
                        time.ticks_ms()
                    )

            else:

                traffic_centered_since_ms = 0


            centered_ms = 0

            if traffic_centered_since_ms != 0:

                centered_ms = time.ticks_diff(
                    now,
                    traffic_centered_since_ms
                )


            recenter_confirmed = (
                centered_ms >= settings.RECENTER_CONFIRM_MS
            )

            recenter_timed_out = (
                elapsed >= settings.RECENTER_CAMERA_TIMEOUT_MS
            )


            if recenter_confirmed or recenter_timed_out:

                print("")
                print("TRAFFIC PASS COMPLETE")

                if recenter_timed_out and not recenter_confirmed:

                    print(
                        "(camera recenter timed out,",
                        "continuing on last known heading)"
                    )

                print(
                    "90 DEGREE TURN COUNT:",
                    total_turns
                )
                print("")


                active_traffic_color = None
                active_traffic_direction = None

                traffic_lost_count = 0
                traffic_recenter_phase = 0
                traffic_centered_since_ms = 0


                last_traffic_completed_ms = (
                    time.ticks_ms()
                )


                # No corner count here.
                #
                # A pillar manoeuvre is not one of the twelve
                # track corners.
                state = DRIVING

                continue


    # ========================================================
    # APPROACH TRACK WALL
    # ========================================================

    elif state == CORNER_APPROACH:

        car.forward(
            settings.CORNER_APPROACH_SPEED
        )


        distance = update_front_distance()


        # ----------------------------------------------------
        # Keep checking for a pillar while approaching what we
        # believe is the wall. A closer, larger blob is far more
        # reliable than the original distant classification read,
        # so a misclassified wall can still be corrected here
        # instead of driving straight into an unavoidable pillar.
        # ----------------------------------------------------

        if (
            is_valid_distance(distance)
            and
            distance > settings.WALL_RECHECK_MIN_CM
        ):

            traffic = scan_traffic_sign()

            if traffic is not None:

                active_traffic_color = (
                    traffic["color"]
                )

                active_traffic_direction = (
                    traffic["direction"]
                )

                active_traffic_cx = (
                    traffic["cx"]
                )

                traffic_seen_on_current_straight = True

                active_corner_direction = None


                print("")
                print("WALL RECLASSIFIED AS PILLAR")
                print(
                    active_traffic_color.upper(),
                    "PASS:",
                    active_traffic_direction.upper()
                )
                print("")


                state = TRAFFIC_APPROACH

                continue


        if (
            is_valid_distance(distance)
            and
            distance <= settings.TURN_TRIGGER_CM
        ):

            record_straight_before_corner()


            print("")
            print("================================")
            print(
                "START 90 DEGREE TURN:",
                active_corner_direction.upper()
            )
            print(
                "DISTANCE:",
                distance,
                "cm"
            )
            print("================================")
            print("")


            turn_started_ms = (
                time.ticks_ms()
            )

            turn_saw_close_wall = False


            drive_corner(
                active_corner_direction
            )


            state = CORNER_TURNING

            continue


    # ========================================================
    # 90 DEGREE TRACK TURN
    # ========================================================

    elif state == CORNER_TURNING:

        drive_corner(
            active_corner_direction
        )


        elapsed = time.ticks_diff(
            now,
            turn_started_ms
        )


        distance = (
            ultrasonic.get_stable_distance()
        )


        # ----------------------------------------------------
        # Never leave the car turning forever.
        # ----------------------------------------------------

        if elapsed >= settings.TURN_TIMEOUT_MS:

            print(
                "TURN TIMEOUT -> TRIM"
            )

            corner_trim_started_ms = (
                time.ticks_ms()
            )

            state = CORNER_TRIM

            continue


        # ----------------------------------------------------
        # STAGE 1: confirm the sensor has actually swept close
        # past the old wall before we start looking for release.
        # ----------------------------------------------------

        if not turn_saw_close_wall:

            if (
                is_valid_distance(distance)
                and
                distance <= settings.TURN_WALL_CLOSE_CM
            ):

                turn_saw_close_wall = True

                print(
                    "TURN: close wall confirmed",
                    distance,
                    "cm"
                )


        # ----------------------------------------------------
        # STAGE 2: once the close wall has been seen, wait for
        # the reading to grow again. That means the ultrasonic
        # has swept away from the old wall and toward the new
        # straight, and the pivot is done.
        # ----------------------------------------------------

        else:

            if (
                elapsed >= settings.TURN_MIN_MS
                and
                (
                    not is_valid_distance(distance)
                    or
                    distance
                    >=
                    settings.TURN_CLEAR_DISTANCE_CM
                )
            ):

                print(
                    "TURN RELEASE:",
                    distance,
                    "cm"
                )


                corner_trim_started_ms = (
                    time.ticks_ms()
                )


                state = CORNER_TRIM

                continue


    # ========================================================
    # CORNER TRIM
    # ========================================================
    #
    # A short final pivot at reduced speed. The ultrasonic reports
    # "released" slightly before the car has actually completed a
    # full 90 degrees, so this trims the remaining angle instead of
    # stopping the instant release is detected.

    elif state == CORNER_TRIM:

        elapsed = time.ticks_diff(
            now,
            corner_trim_started_ms
        )


        if elapsed < settings.TURN_TRIM_MS:

            drive_corner(
                active_corner_direction,
                speed=settings.TURN_TRIM_SPEED
            )

            continue


        print(
            "TURN COMPLETE -> RECOVERY"
        )


        car.stop()

        time.sleep_ms(30)

        car.forward(
            settings.CORNER_EXIT_SPEED
        )


        corner_recovery_started_ms = (
            time.ticks_ms()
        )


        state = CORNER_RECOVERY

        continue


    # ========================================================
    # CORNER RECOVERY
    # ========================================================

    elif state == CORNER_RECOVERY:

        car.forward(
            settings.CORNER_EXIT_SPEED
        )


        elapsed = time.ticks_diff(
            now,
            corner_recovery_started_ms
        )


        if elapsed >= settings.CORNER_RECOVERY_MS:

            # This is the only point at which a physical track
            # corner is officially counted.
            count_completed_corner()


            active_corner_direction = None


            # ------------------------------------------------
            # TWELVE CORNERS = THREE LAPS
            # ------------------------------------------------

            if total_turns >= settings.TOTAL_TURNS:

                finish_drive_ms = (
                    estimate_finish_drive_time()
                )


                print("")
                print("================================")
                print("THREE LAPS COMPLETE")
                print(
                    "RETURN-TO-START ESTIMATE:",
                    finish_drive_ms,
                    "ms"
                )
                print("================================")
                print("")


                finish_started_ms = (
                    time.ticks_ms()
                )


                state = FINISH_RETURN

                continue


            # ------------------------------------------------
            # Start measuring the next straight.
            # ------------------------------------------------

            straight_started_ms = (
                time.ticks_ms()
            )

            traffic_seen_on_current_straight = False


            state = DRIVING

            continue


    # ========================================================
    # APPROXIMATE RETURN TO STARTING POSITION
    # ========================================================

    elif state == FINISH_RETURN:

        elapsed = time.ticks_diff(
            now,
            finish_started_ms
        )


        if elapsed < finish_drive_ms:

            car.forward(
                settings.FINISH_SPEED
            )


        else:

            car.stop()

            state = FINISHED

            continue


    # Small scheduler pause.
    time.sleep_ms(10)