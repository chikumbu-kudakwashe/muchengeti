# ============================================================
# PARALLEL PARKING - STANDALONE
# ============================================================
#
# Power the robot on, it waits STARTUP_DELAY_S seconds (so you can
# place it and step back), then performs the parking manoeuvre on
# its own. Not wired into main.py yet - run this file directly on
# the board to test parking in isolation.
#
# Built on the project's own hardware classes (hardware.car.Car /
# hardware.ultrasonic.UltrasonicScanner) so it drives through the
# same motor/ultrasonic path as main.py.
#
# IMPORTANT - IF THE ROBOT SPINS INSTEAD OF STRAFING:
# strafe_left()/strafe_right() command the classic mecanum "X"
# pattern (diagonally opposite wheels driven the same direction).
# If the robot rotates in place instead of sliding sideways, that
# almost always means one of the four mecanum wheels is mounted in
# the wrong corner (each wheel's rollers only form the correct "X"
# from one specific position - front-left/right and rear-left/
# right wheels are NOT interchangeable). Forward/backward/rotate
# still look correct in that situation because those motions don't
# depend on roller orientation, which is why this can go unnoticed
# until strafing is tried. Check the wheel positions against the
# kit's diagram before assuming this script's logic is at fault.

import time

import hardware.car as Car
import hardware.ultrasonic as Ultrasonic


# ============================================================
# HARDWARE
# ============================================================

car = Car.Car()

ultrasonic = Ultrasonic.UltrasonicScanner()


# ============================================================
# SETTINGS
# ============================================================

# Wait this long after power-on before the manoeuvre starts.
STARTUP_DELAY_S = 5

# Final stop distance from the wall inside the bay.
TARGET_FRONT_DIST_CM = 4.0

PARKING_SPEED = 120

# "right" or "left"
STRAFE_DIRECTION = "right"

# Safety net: never strafe for longer than this looking for the
# bay wall, in case the ultrasonic never sees it (misalignment,
# missed bay, sensor fault).
MAX_PARK_TIME_MS = 4000


# ============================================================
# PARKING MANOEUVRE
# ============================================================

def parallel_park() -> bool:
    """
    Strafe sideways until the front ultrasonic sees the back wall
    of the parking bay, then stop.

    Returns:
        True if the target distance was reached, False if the
        safety timeout was hit first.
    """

    print("")
    print("==============================")
    print("PARALLEL PARKING")
    print("Direction:", STRAFE_DIRECTION)
    print("Target distance:", TARGET_FRONT_DIST_CM, "cm")
    print("==============================")
    print("")

    start_ms = time.ticks_ms()

    while True:

        elapsed = time.ticks_diff(
            time.ticks_ms(),
            start_ms
        )

        if elapsed >= MAX_PARK_TIME_MS:

            car.stop()

            print("")
            print("PARKING TIMEOUT - wall never reached")
            print("")

            return False


        distance = ultrasonic.get_stable_distance()

        print("Front distance:", distance, "cm")


        if distance <= TARGET_FRONT_DIST_CM:

            car.stop()

            print("")
            print("PARKING COMPLETE")
            print("")

            return True


        if STRAFE_DIRECTION == "right":
            car.strafe_right(PARKING_SPEED)
        else:
            car.strafe_left(PARKING_SPEED)

        time.sleep_ms(50)


# ============================================================
# STARTUP
# ============================================================

car.stop()

print("")
print("Parking starts in", STARTUP_DELAY_S, "seconds...")

time.sleep(STARTUP_DELAY_S)


try:

    parallel_park()

except KeyboardInterrupt:
    print("")
    print("Test stopped by user")

finally:
    car.stop()
