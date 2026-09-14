import time

import libs.ACB_SmartCar_V2
import libs.ultrasonic
import libs.servo


# ---------------------------------------------------------
# Pin configuration
# ---------------------------------------------------------

TRIG_PIN = 13
ECHO_PIN = 14
SERVO_PIN = 25

# Check distance
OBSTACLE_DISTANCE = 25

FRONT_ANGLE = 90
RIGHT_ANGLE = 10
LEFT_ANGLE = 170

FORWARD_SPEED = 150
REVERSE_SPEED = 180
TURN_SPEED = 180

REVERSE_TIME = 0.5
TURN_TIME = 1.0

SERVO_SETTLE_TIME = 0.25


# ---------------------------------------------------------
# Set up the car, servo and ultrasonic sensor
# ---------------------------------------------------------

car = libs.ACB_SmartCar_V2.ACB_SmartCar_V2()

servo = libs.servo.Servo()
servo.attach(SERVO_PIN)

ultrasonic = libs.ultrasonic.ACB_Ultrasonic(
    TRIG_PIN,
    ECHO_PIN
)


# Make sure the car is stopped when the program starts.
car.Move(car.Stop, 0)

# Keep the ultrasonic sensor facing forward by default.
servo.write(FRONT_ANGLE)


# ---------------------------------------------------------
# Distance functions
# ---------------------------------------------------------

def get_stable_distance(samples=3):
    """
    Take a few ultrasonic readings instead of trusting one reading.
    Ultrasonic sensors can sometimes give random values.
    """

    readings = []

    for _ in range(samples):
        distance = ultrasonic.get_distance()

        # Ignore readings that do not make sense.
        if distance > 0:
            readings.append(distance)

        time.sleep(0.02)

    # If all readings failed, return a large distance.
    # This stops the car from reacting to a bad sensor reading.
    if not readings:
        return 999

    readings.sort()

    # Use the middle value so one strange reading does not affect us.
    return readings[len(readings) // 2]


def look_forward():
    """
    Point the ultrasonic sensor forward and get the distance.
    """

    servo.write(FRONT_ANGLE)
    time.sleep(SERVO_SETTLE_TIME)

    return get_stable_distance()


def look_right():
    """
    Check how much space is available on the right side.
    """

    servo.write(RIGHT_ANGLE)
    time.sleep(SERVO_SETTLE_TIME)

    return get_stable_distance()


def look_left():
    """
    Check how much space is available on the left side.
    """

    servo.write(LEFT_ANGLE)
    time.sleep(SERVO_SETTLE_TIME)

    return get_stable_distance()


def scan_sides():
    """
    Look right and left when something is blocking the front.

    The sensor is returned to the centre when the scan is finished.
    """

    car.Move(car.Stop, 0)

    right_distance = look_right()
    left_distance = look_left()

    # Put the ultrasonic sensor back in the forward position.
    servo.write(FRONT_ANGLE)
    time.sleep(SERVO_SETTLE_TIME)

    return left_distance, right_distance


# ---------------------------------------------------------
# Basic car movement
# ---------------------------------------------------------

def stop():
    car.Move(car.Stop, 0)


def move_forward():
    car.Move(car.Forward, FORWARD_SPEED)


def move_backward():
    car.Move(car.Backward, REVERSE_SPEED)


def turn_left():
    """
    Move back slightly before turning left.

    For now the turn is still based on time.
    Later this should use the camera or sensor feedback.
    """

    move_backward()
    time.sleep(REVERSE_TIME)

    car.Move(car.Contrarotate, TURN_SPEED)
    time.sleep(TURN_TIME)

    stop()


def turn_right():
    """
    Move back slightly before turning right.

    For now the turn is still based on time.
    Later this should use the camera or sensor feedback.
    """

    move_backward()
    time.sleep(REVERSE_TIME)

    car.Move(car.Clockwise, TURN_SPEED)
    time.sleep(TURN_TIME)

    stop()


def reverse_and_turn_around():
    """
    Used when both sides are blocked.

    The car moves backwards and rotates to find another route.
    """

    move_backward()
    time.sleep(REVERSE_TIME)

    car.Move(car.Contrarotate, TURN_SPEED)
    time.sleep(TURN_TIME)

    stop()


# ---------------------------------------------------------
# Obstacle avoidance
# ---------------------------------------------------------

def avoid_obstacle():
    """
    Stop the car, check both sides and move towards
    the side with more free space.
    """

    stop()

    left_distance, right_distance = scan_sides()

    print(
        "Left:",
        round(left_distance, 1),
        "cm | Right:",
        round(right_distance, 1),
        "cm"
    )

    # If both sides are blocked, back away and turn around.
    if (
        right_distance < OBSTACLE_DISTANCE
        and left_distance < OBSTACLE_DISTANCE
    ):
        print("Both sides blocked")
        reverse_and_turn_around()

    # There is more space on the right.
    elif right_distance > left_distance:
        print("More space on the right")
        turn_right()

    # There is more space on the left.
    elif left_distance > right_distance:
        print("More space on the left")
        turn_left()

    # If both readings are almost the same,
    # just choose right for now.
    else:
        print("Both sides look similar, choosing right")
        turn_right()


# ---------------------------------------------------------
# Main loop
# ---------------------------------------------------------

try:

    while True:

        # Most of the time the ultrasonic sensor stays
        # facing forward while the car is moving.
        middle_distance = look_forward()

        print(
            "Front:",
            round(middle_distance, 1),
            "cm"
        )

        # Something is too close, so stop and check both sides.
        if middle_distance <= OBSTACLE_DISTANCE:
            print("Obstacle detected")
            avoid_obstacle()

        else:
            # Nothing is blocking the front, keep moving.
            move_forward()


except KeyboardInterrupt:

    # Stop the car properly when I stop the program.
    stop()
    servo.write(FRONT_ANGLE)

    print("Program stopped")