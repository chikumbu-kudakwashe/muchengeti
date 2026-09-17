# ============================================================
# PARALLEL PARKING TEST (Sideways Only)
# ============================================================
#
# Standalone test built on the project's own hardware classes
# (hardware.car.Car / hardware.ultrasonic.UltrasonicScanner) so it
# drives through the same motor/ultrasonic path main.py uses.
#
# Strafes sideways until the front ultrasonic sees the bay wall
# at TARGET_FRONT_DIST_CM, then stops.
#
# Run this directly on the board - it is not imported by anything.

import time

import hardware.car as Car
import hardware.ultrasonic as Ultrasonic


# ============================================================
# HARDWARE
# ============================================================

car = Car.Car()

ultrasonic = Ultrasonic.UltrasonicScanner()


# ============================================================
# PARKING SETTINGS
# ============================================================

TARGET_FRONT_DIST_CM = 4.0   # final stop inside bay

PARKING_SPEED = 120

# "right" or "left"
STRAFE_DIRECTION = "right"


# ============================================================
# STATES
# ============================================================

STRAFE_IN = 0
PARKED = 1

state = STRAFE_IN


# ============================================================
# MAIN LOOP (Sideways Only)
# ============================================================

print("")
print("==============================")
print("PARKING TEST (sideways only)")
print("Strafe direction:", STRAFE_DIRECTION)
print("Target front distance:", TARGET_FRONT_DIST_CM, "cm")
print("==============================")
print("")

try:

    while True:

        if state == STRAFE_IN:

            distance = ultrasonic.get_stable_distance()

            print("Front distance:", distance, "cm")

            if distance > TARGET_FRONT_DIST_CM:

                if STRAFE_DIRECTION == "right":
                    car.strafe_right(PARKING_SPEED)
                else:
                    car.strafe_left(PARKING_SPEED)

            else:
                car.stop()

                print("Parking complete")

                state = PARKED

        elif state == PARKED:
            car.stop()

            print("ROBOT PARKED")

            time.sleep_ms(100)

        time.sleep_ms(50)

except KeyboardInterrupt:
    print("")
    print("Test stopped by user")

finally:
    car.stop()
