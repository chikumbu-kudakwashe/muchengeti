from machine import Pin, PWM
from libs import ACB_Canmv
import time


# --------------------------------------------------
# CAMERA
# --------------------------------------------------

cam = ACB_Canmv.ACB_Canmv()

# ACEBOTT colour indexes
RED_INDEX = 1
GREEN_INDEX = 2

PIXELS_TH = 200
AREA_TH = 200


# --------------------------------------------------
# LEDS
# --------------------------------------------------

LEFT_LED_PIN = 2
RIGHT_LED_PIN = 12

left_led = Pin(LEFT_LED_PIN, Pin.OUT)
right_led = Pin(RIGHT_LED_PIN, Pin.OUT)

left_led.value(0)
right_led.value(0)


# --------------------------------------------------
# BUZZER
# --------------------------------------------------

BUZZER_PIN = 33


def beep(duration_ms=120):

    buzzer = PWM(
        Pin(BUZZER_PIN),
        freq=1000,
        duty=512
    )

    time.sleep_ms(duration_ms)

    buzzer.deinit()


# --------------------------------------------------
# CAMERA STARTUP
# --------------------------------------------------

print("Starting camera...")

cam.init(
    cam.SDA,
    cam.SCL
)

time.sleep_ms(500)

print("Camera ready")


# --------------------------------------------------
# COLOR CHECK FUNCTIONS
# --------------------------------------------------

def check_red():

    detected = cam.color_recognize(
        RED_INDEX,
        PIXELS_TH,
        AREA_TH
    )

    if detected:

        print("----------------------")
        print("RED DETECTED")
        print("Tag:", cam.getTag)

        print(
            "X,Y,W,H:",
            cam.getX,
            cam.getY,
            cam.getW,
            cam.getH
        )

        # Left LED for red
        left_led.value(1)
        right_led.value(0)

        beep()

        return True

    return False


def check_green():

    detected = cam.color_recognize(
        GREEN_INDEX,
        PIXELS_TH,
        AREA_TH
    )

    if detected:

        print("----------------------")
        print("GREEN DETECTED")
        print("Tag:", cam.getTag)

        print(
            "X,Y,W,H:",
            cam.getX,
            cam.getY,
            cam.getW,
            cam.getH
        )

        # Right LED for green
        left_led.value(0)
        right_led.value(1)

        beep()

        return True

    return False


# --------------------------------------------------
# MAIN LOOP
# --------------------------------------------------

while True:

    detected = False

    # Check red
    if check_red():
        detected = True

    time.sleep_ms(100)

    # Check green
    if check_green():
        detected = True

    if not detected:

        left_led.value(0)
        right_led.value(0)

        print("No red or green detected")

    time.sleep_ms(100)