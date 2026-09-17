# ============================================================
# TRAFFIC BLOB CALIBRATION
# ============================================================
#
# Prints raw, UNFILTERED K210 detections (colour, width, height,
# pixels, cx/cy) continuously. Use this to find real threshold
# numbers instead of guessing:
#
# 1. Run this on the robot with the K210 in view of, in turn:
#      - the orange/red corner-direction line on the mat
#      - a RED pillar
#      - a GREEN pillar
#    at a few different distances (far, at TRAFFIC_PASS_TRIGGER_CM,
#    close).
#
# 2. Read off the printed width/height/pixels for each case.
#
# 3. Pick config/settings.py's TRAFFIC_MIN_HEIGHT/TRAFFIC_MIN_WIDTH/
#    TRAFFIC_MIN_PIXELS so real pillar readings clear the threshold
#    at the distance you actually want to detect them, while the
#    mat line's readings do not.
#
# Not wired into main.py - standalone diagnostic only.

import time

from libs.k210_link import K210Link
import config.settings as settings


link = K210Link(
    settings.K210_RX_PIN,
    settings.K210_TX_PIN,
    settings.K210_BAUD
)

# See everything, not just red/green - useful for comparing the
# mat's orange line against BLUE too if that ever needs tuning.
link.set_mode(K210Link.MODE_ALL)

print("")
print("==============================")
print("TRAFFIC BLOB CALIBRATION")
print("==============================")
print("Present each target and read the numbers below.")
print("")

while True:

    found = link.poll()

    if found:

        print(
            link.name.upper(),
            "W:", link.w,
            "H:", link.h,
            "PIXELS:", link.pixels,
            "CX:", link.cx,
            "CY:", link.cy
        )

    else:

        print("NONE")

    time.sleep_ms(150)
