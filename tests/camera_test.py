from libs import ACB_Canmv
import time


# ---------------------------------------------------------
# Camera settings
# ---------------------------------------------------------

COLOR_ALL = 0
COLOR_RED = 1
COLOR_GREEN = 2
COLOR_BLUE = 3

PIXELS_THRESHOLD = 600
AREA_THRESHOLD = 100


# ---------------------------------------------------------
# Start camera
# ---------------------------------------------------------

camera = ACB_Canmv.ACB_Canmv()

camera.init()

print("Camera colour recognition started")


# ---------------------------------------------------------
# Main test
# ---------------------------------------------------------

while True:

    detected = camera.color_recognize(
        COLOR_ALL,
        PIXELS_THRESHOLD,
        AREA_THRESHOLD
    )

    if detected:

        print("------------------------------")

        print(
            "Tag:",
            camera.getTag
        )

        print(
            "Position:",
            camera.getX,
            camera.getY
        )

        print(
            "Size:",
            camera.getW,
            camera.getH
        )

        print(
            "Centre:",
            camera.getCX,
            camera.getCY
        )

    time.sleep_ms(50)