from libs import ACB_Canmv
import time


# Camera color indexes used by the Acebott AI CAMMV.
COLOR_ALL = 0
COLOR_RED = 1
COLOR_GREEN = 2
COLOR_BLUE = 3


# Start with all-color recognition. Change this to COLOR_RED,
# COLOR_GREEN, or COLOR_BLUE for a single color.
COLOR_INDEX = COLOR_ALL
PIXELS_THRESHOLD = 200
AREA_THRESHOLD = 200


# ESP32 UART1 connection to the camera.
CAMERA_RX_PIN = 16
CAMERA_TX_PIN = 17
CAMERA_BAUDRATE = 115200
CAMERA_UART_ID = 1


camera = ACB_Canmv.ACB_Canmv()
camera.init(
    rx_pin=CAMERA_RX_PIN,
    tx_pin=CAMERA_TX_PIN,
    baudrate=CAMERA_BAUDRATE,
    uart_id=CAMERA_UART_ID
)

print("Acebott AI CAMMV color recognition started")
print("Color index:", COLOR_INDEX)
print("Pixels threshold:", PIXELS_THRESHOLD)
print("Area threshold:", AREA_THRESHOLD)


while True:
    detected = camera.color_recognize(
        COLOR_INDEX,
        PIXELS_THRESHOLD,
        AREA_THRESHOLD
    )

    if detected:
        print("------------------------------")
        print("Tag:", camera.getTag)
        print("Position:", camera.getX, camera.getY)
        print("Size:", camera.getW, camera.getH)
        print("Centre:", camera.getCX, camera.getCY)

    time.sleep_ms(50)
