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
11. Signal turns and pillar passes on the indicator LEDs.

Parking will be added as the next phase.

All of the non-state-machine logic (distance smoothing, traffic
scanning/sizing, corner pivoting, lap/finish timing, LEDs) lives in
navigation.race.Race - this file is only the state machine.
"""

import time

import config.settings as settings

import hardware.car as Car
import hardware.ultrasonic as Ultrasonic
import hardware.leds as Leds

from libs.k210_link import K210Link

from navigation.startup import StartupDirectionDetector
from navigation.traffic import TrafficColorDetector
from navigation.race import Race, is_valid_distance


# ============================================================
# HARDWARE
# ============================================================

car = Car.Car()

ultrasonic = Ultrasonic.UltrasonicScanner()

leds = Leds.Leds(
    settings.LED_LEFT_PIN,
    settings.LED_RIGHT_PIN,
    settings.LED_PWM_FREQ
)

# Text-protocol K210 vision link (see libs/k210_link.py) - replaces
# the old ACB_Canmv binary-packet camera driver.
link = K210Link(
    settings.K210_RX_PIN,
    settings.K210_TX_PIN,
    settings.K210_BAUD
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
# DETECTORS / RACE SUPPORT
# ============================================================

startup_detector = StartupDirectionDetector(
    link=link,
    min_width=settings.START_COLOR_MIN_WIDTH,
    min_height=settings.START_COLOR_MIN_HEIGHT,
    min_pixels=settings.START_COLOR_MIN_PIXELS,
    min_votes=settings.START_COLOR_MIN_VOTES,
    scan_ms=settings.STARTUP_SCAN_MS,
    sample_delay_ms=settings.STARTUP_SAMPLE_DELAY_MS,
    blue_direction=settings.BLUE_TURN_DIRECTION,
    alt_direction=settings.ORANGE_TURN_DIRECTION
)

traffic_detector = TrafficColorDetector(
    link=link,
    min_width=settings.TRAFFIC_MIN_WIDTH,
    min_height=settings.TRAFFIC_MIN_HEIGHT,
    min_pixels=settings.TRAFFIC_MIN_PIXELS,
    confirmations=settings.TRAFFIC_CONFIRMATIONS
)

race = Race(
    car,
    ultrasonic,
    traffic_detector,
    leds
)


# ============================================================
# STARTUP
# ============================================================

car.stop()

print("")
print("================================")
print("MUCHENGETI - WRO AUTONOMOUS NAVIGATION")
print("================================")
print("Field:", settings.MAT_SIZE_CM, "x", settings.MAT_SIZE_CM, "cm")
print("Target:", settings.TOTAL_LAPS, "laps /", settings.TOTAL_TURNS, "corners")
print("")

# Startup scan: blue confirmed -> BLUE_TURN_DIRECTION, otherwise
# assumed orange -> ORANGE_TURN_DIRECTION.
race.course_direction = startup_detector.detect()

settings.DEFAULT_TURN_DIRECTION = race.course_direction

print("")
print("COURSE LOCKED:", race.course_direction.upper())
print("")

time.sleep_ms(500)

race.run_started_ms = time.ticks_ms()
race.straight_started_ms = race.run_started_ms


# ============================================================
# MAIN LOOP
# ============================================================

while True:

    now = time.ticks_ms()


    # --------------------------------------------------
    # FINISHED
    # --------------------------------------------------

    if state == FINISHED:

        car.stop()

        print("")
        print("RACE COMPLETE -", settings.TOTAL_LAPS, "laps,", settings.TOTAL_TURNS, "turns")

        break


    # --------------------------------------------------
    # NORMAL DRIVING
    # --------------------------------------------------

    if state == DRIVING:

        car.forward(settings.DRIVE_SPEED)

        distance = race.update_front_distance()

        # Periodic traffic scan - a pillar may not be centered in
        # the ultrasonic beam, so this runs even when nothing close
        # has been detected yet.
        cooldown_done = time.ticks_diff(now, race.last_traffic_completed_ms) >= settings.TRAFFIC_COOLDOWN_MS
        scan_due = time.ticks_diff(now, race.last_traffic_scan_ms) >= settings.TRAFFIC_SCAN_INTERVAL_MS

        if cooldown_done and scan_due:

            race.last_traffic_scan_ms = now

            traffic = race.scan_traffic_sign()

            if traffic is not None:

                race.lock_traffic(traffic)

                print("PILLAR LOCKED:", race.active_traffic_color.upper(), "PASS:", race.active_traffic_direction.upper())

                state = TRAFFIC_APPROACH

                continue

        # Something is close - slow down and classify it before a
        # camera-switch delay lets us hit it at full speed.
        if is_valid_distance(distance) and distance <= settings.BOUNDARY_CLASSIFY_CM:

            car.forward(settings.CLASSIFICATION_SPEED)

            traffic = race.scan_traffic_sign()

            if traffic is not None:

                race.lock_traffic(traffic)

                race.wall_no_color_streak = 0

                state = TRAFFIC_APPROACH

                continue

            # A single missed colour read is not enough evidence to
            # commit to an irreversible 90 degree turn.
            race.wall_no_color_streak += 1

            if race.wall_no_color_streak < settings.WALL_CONFIRM_COUNT:

                continue

            race.wall_no_color_streak = 0

            race.lock_corner(race.course_direction)

            print("WALL DETECTED:", distance, "cm -> CORNER", race.active_corner_direction.upper())

            state = CORNER_APPROACH

            continue

        else:

            race.wall_no_color_streak = 0

        # Emergency protection.
        if is_valid_distance(distance) and distance <= settings.EMERGENCY_CM:

            print("EMERGENCY DISTANCE:", distance)

            car.backward(settings.BACKUP_SPEED)

            time.sleep_ms(180)

            car.stop()

            time.sleep_ms(50)

            continue


    # --------------------------------------------------
    # APPROACH LOCKED TRAFFIC PILLAR
    # --------------------------------------------------

    elif state == TRAFFIC_APPROACH:

        car.forward(settings.TRAFFIC_APPROACH_SPEED)

        distance = race.update_front_distance()

        if is_valid_distance(distance) and distance <= settings.TRAFFIC_PASS_TRIGGER_CM:

            print(race.active_traffic_color.upper(), "PILLAR ->", race.active_traffic_direction.upper())

            # Refresh the pillar's camera position - it is now
            # close and large, so this reading is more reliable
            # than the one taken at the original classify distance.
            traffic = race.scan_traffic_sign()

            if traffic is not None and traffic["color"] == race.active_traffic_color:

                race.active_traffic_cx = traffic["cx"]

            race.active_traffic_shift_ms = race.compute_shift_ms(race.active_traffic_cx)

            print("SHIFT SIZE:", race.active_traffic_shift_ms, "ms")

            race.traffic_shift_started_ms = time.ticks_ms()

            race.shift_away_from_pillar(race.active_traffic_direction)

            state = TRAFFIC_SHIFT

            continue


    # --------------------------------------------------
    # SIDESTEP AWAY FROM PILLAR
    # --------------------------------------------------

    elif state == TRAFFIC_SHIFT:

        race.shift_away_from_pillar(race.active_traffic_direction)

        elapsed = time.ticks_diff(now, race.traffic_shift_started_ms)

        if elapsed >= race.active_traffic_shift_ms:

            car.forward(settings.TRAFFIC_PASS_SPEED)

            race.traffic_pass_started_ms = time.ticks_ms()

            race.traffic_lost_count = 0

            state = TRAFFIC_PASS

            continue


    # --------------------------------------------------
    # DRIVE PAST THE PILLAR
    # --------------------------------------------------

    elif state == TRAFFIC_PASS:

        car.forward(settings.TRAFFIC_PASS_SPEED)

        elapsed = time.ticks_diff(now, race.traffic_pass_started_ms)

        if elapsed >= settings.TRAFFIC_MIN_PASS_MS:

            traffic = race.scan_traffic_sign()

            if traffic is not None and traffic["color"] == race.active_traffic_color:

                race.traffic_lost_count = 0

            else:

                race.traffic_lost_count += 1

            if race.traffic_lost_count >= settings.TRAFFIC_LOST_CONFIRMATIONS:

                print("PILLAR CLEARED -> RECENTER")

                race.traffic_recenter_started_ms = time.ticks_ms()
                race.traffic_recenter_phase = 0

                race.shift_back_to_route(race.active_traffic_direction)

                state = TRAFFIC_RECENTER

                continue

        if elapsed >= settings.TRAFFIC_MAX_PASS_MS:

            print("PILLAR PASS TIMEOUT -> RECENTER")

            race.traffic_recenter_started_ms = time.ticks_ms()
            race.traffic_recenter_phase = 0

            race.shift_back_to_route(race.active_traffic_direction)

            state = TRAFFIC_RECENTER

            continue


    # --------------------------------------------------
    # RETURN TO ROUTE AFTER PILLAR
    # --------------------------------------------------

    elif state == TRAFFIC_RECENTER:

        elapsed = time.ticks_diff(now, race.traffic_recenter_started_ms)

        # Phase 0: undo the diagonal lean.
        if race.traffic_recenter_phase == 0:

            race.shift_back_to_route(race.active_traffic_direction)

            if elapsed >= race.active_traffic_shift_ms:

                race.traffic_recenter_phase = 1

                race.traffic_recenter_started_ms = time.ticks_ms()

                car.forward(settings.CORNER_EXIT_SPEED)

        # Phase 1: drive straight for a fixed time before handing
        # back to normal driving. The K210 no longer reports a
        # line-following error (see navigation/race.py history),
        # so there is nothing left to confirm actual center with -
        # this is a plain timed forward burst, same as the shift.
        else:

            car.forward(settings.CORNER_EXIT_SPEED)

            if elapsed >= settings.RECENTER_FORWARD_MS:

                print("TRAFFIC PASS COMPLETE - TURN COUNT:", race.total_turns)

                # No corner count here - a pillar manoeuvre is not
                # one of the twelve track corners.
                race.clear_traffic()

                state = DRIVING

                continue


    # --------------------------------------------------
    # APPROACH TRACK WALL
    # --------------------------------------------------

    elif state == CORNER_APPROACH:

        car.forward(settings.CORNER_APPROACH_SPEED)

        distance = race.update_front_distance()

        # Keep checking for a pillar while approaching what we
        # believe is the wall - a closer, larger blob is far more
        # reliable than the original distant classification read.
        if is_valid_distance(distance) and distance > settings.WALL_RECHECK_MIN_CM:

            traffic = race.scan_traffic_sign()

            if traffic is not None:

                race.lock_traffic(traffic)

                race.active_corner_direction = None

                print("WALL RECLASSIFIED AS PILLAR:", race.active_traffic_color.upper())

                state = TRAFFIC_APPROACH

                continue

        if is_valid_distance(distance) and distance <= settings.TURN_TRIGGER_CM:

            race.record_straight_before_corner()

            print("START 90 DEGREE TURN:", race.active_corner_direction.upper(), "at", distance, "cm")

            race.turn_started_ms = time.ticks_ms()
            race.turn_saw_close_wall = False

            race.drive_corner(race.active_corner_direction)

            state = CORNER_TURNING

            continue


    # --------------------------------------------------
    # 90 DEGREE TRACK TURN
    # --------------------------------------------------

    elif state == CORNER_TURNING:

        race.drive_corner(race.active_corner_direction)

        elapsed = time.ticks_diff(now, race.turn_started_ms)

        distance = ultrasonic.get_stable_distance()

        if elapsed >= settings.TURN_TIMEOUT_MS:

            print("TURN TIMEOUT -> TRIM")

            race.corner_trim_started_ms = time.ticks_ms()

            state = CORNER_TRIM

            continue

        # Stage 1: confirm the sensor has actually swept close past
        # the old wall before looking for it to release.
        if not race.turn_saw_close_wall:

            if is_valid_distance(distance) and distance <= settings.TURN_WALL_CLOSE_CM:

                race.turn_saw_close_wall = True

                print("TURN: close wall confirmed", distance, "cm")

        # Stage 2: once the close wall has been seen, the pivot is
        # done once the reading grows again.
        else:

            released = not is_valid_distance(distance) or distance >= settings.TURN_CLEAR_DISTANCE_CM

            if elapsed >= settings.TURN_MIN_MS and released:

                print("TURN RELEASE:", distance, "cm")

                race.corner_trim_started_ms = time.ticks_ms()

                state = CORNER_TRIM

                continue


    # --------------------------------------------------
    # CORNER TRIM
    # --------------------------------------------------
    #
    # A short final pivot at reduced speed. The ultrasonic reports
    # "released" slightly before the car has actually completed a
    # full 90 degrees, so this trims the remaining angle.

    elif state == CORNER_TRIM:

        elapsed = time.ticks_diff(now, race.corner_trim_started_ms)

        if elapsed < settings.TURN_TRIM_MS:

            race.drive_corner(race.active_corner_direction, speed=settings.TURN_TRIM_SPEED)

            continue

        print("TURN COMPLETE -> RECOVERY")

        car.stop()

        time.sleep_ms(30)

        car.forward(settings.CORNER_EXIT_SPEED)

        race.corner_recovery_started_ms = time.ticks_ms()

        state = CORNER_RECOVERY

        continue


    # --------------------------------------------------
    # CORNER RECOVERY
    # --------------------------------------------------

    elif state == CORNER_RECOVERY:

        car.forward(settings.CORNER_EXIT_SPEED)

        elapsed = time.ticks_diff(now, race.corner_recovery_started_ms)

        if elapsed >= settings.CORNER_RECOVERY_MS:

            # This is the only point a physical track corner is
            # officially counted.
            race.count_completed_corner()

            race.clear_corner()

            if race.total_turns >= settings.TOTAL_TURNS:

                race.finish_drive_ms = race.estimate_finish_drive_time()

                print("THREE LAPS COMPLETE - RETURN ESTIMATE:", race.finish_drive_ms, "ms")

                race.finish_started_ms = time.ticks_ms()

                state = FINISH_RETURN

                continue

            race.straight_started_ms = time.ticks_ms()
            race.traffic_seen_on_current_straight = False

            state = DRIVING

            continue


    # --------------------------------------------------
    # APPROXIMATE RETURN TO STARTING POSITION
    # --------------------------------------------------

    elif state == FINISH_RETURN:

        elapsed = time.ticks_diff(now, race.finish_started_ms)

        if elapsed < race.finish_drive_ms:

            car.forward(settings.FINISH_SPEED)

        else:

            car.stop()

            state = FINISHED

            continue


    time.sleep_ms(10)
