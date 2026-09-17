import time

from libs import ACB_Canmv
from navigation.traffic import TrafficColorDetector


cam = ACB_Canmv.ACB_Canmv()

cam.init(
    cam.SDA,
    cam.SCL
)

time.sleep_ms(1000)


detector = TrafficColorDetector(
    cam,

    red_index=1,
    green_index=2,

    # More permissive.
    pixels_threshold=60,
    area_threshold=60,

    # Only reject very small noise.
    min_width=5,
    min_height=5,
    min_area=40,

    # For testing, trust one valid detection.
    confirmations=1
)


print("")
print("==============================")
print("TRAFFIC COLOR TEST")
print("==============================")
print("")


while True:

    result = detector.detect()

    if result is not None:

        print(
            result["color"].upper(),
            ": TURN",
            result["direction"].upper(),
            "| W:",
            result["width"],
            "H:",
            result["height"],
            "AREA:",
            result["area"]
        )

    time.sleep_ms(80)