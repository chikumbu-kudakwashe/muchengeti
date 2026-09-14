from machine import UART, Pin
import time

TX_PIN = 17  
RX_PIN = 16  

Forward           = 163
Backward          = 92
Move_Left         = 106
Move_Right        = 149
Top_Left          = 34
Bottom_Left       = 72
Top_Right         = 129
Bottom_Right      = 20
Stop              = 0
Contrarotate      = 83
Clockwise         = 172


class ACB_SmartCar_V2:
    def __init__(self):

        self.Forward = Forward
        self.Backward = Backward
        self.Move_Left = Move_Left
        self.Move_Right = Move_Right
        self.Top_Left = Top_Left
        self.Bottom_Left = Bottom_Left
        self.Top_Right = Top_Right
        self.Bottom_Right = Bottom_Right
        self.Stop = Stop
        self.Contrarotate = Contrarotate
        self.Clockwise = Clockwise

        self.uart = UART(2, baudrate=9600, tx=Pin(TX_PIN), rx=Pin(RX_PIN))
        time.sleep(0.2)  # Short delay to ensure UART is stable

        for i in range(1, 5):
            self.motorControl(i, 0)

    def motorControl(self, motor, speed):

        if self.uart is None:
            return  # Safety check

        if motor in (1, 2):
            dir_val = 1 if speed > 0 else 2
        elif motor in (3, 4):
            dir_val = 2 if speed > 0 else 1
        else:
            return  # Invalid motor index

        speed_value = int(40 + abs(speed) * 60 / 255)

        if speed_value == 40:
            speed_value = 0

        data = bytes([motor, dir_val, speed_value]) + b'\r\n'
        self.uart.write(data)

    def Move(self, Dir, Speed=0):


        # Move forward: all motors forward
        if Dir == Forward:
            for i in range(1, 5):
                self.motorControl(i, Speed)

        # Move backward: all motors backward
        elif Dir == Backward:
            for i in range(1, 5):
                self.motorControl(i, -Speed)

        # Move right: mecanum wheel strafe right
        elif Dir == Move_Right:
            self.motorControl(1, Speed)
            self.motorControl(2, -Speed)
            self.motorControl(3, -Speed)
            self.motorControl(4, Speed)

        # Move left: mecanum wheel strafe left
        elif Dir == Move_Left:
            self.motorControl(1, -Speed)
            self.motorControl(2, Speed)
            self.motorControl(3, Speed)
            self.motorControl(4, -Speed)

        # Rotate clockwise
        elif Dir == Clockwise:
            self.motorControl(1, Speed)
            self.motorControl(2, Speed)
            self.motorControl(3, -Speed)
            self.motorControl(4, -Speed)

        # Rotate counterclockwise
        elif Dir == Contrarotate:
            self.motorControl(1, -Speed)
            self.motorControl(2, -Speed)
            self.motorControl(3, Speed)
            self.motorControl(4, Speed)

        # Move top-left (diagonal)
        elif Dir == Top_Left:
            self.motorControl(1, 0)
            self.motorControl(2, Speed)
            self.motorControl(3, Speed)
            self.motorControl(4, 0)

        # Move top-right (diagonal)
        elif Dir == Top_Right:
            self.motorControl(1, Speed)
            self.motorControl(2, 0)
            self.motorControl(3, 0)
            self.motorControl(4, Speed)

        # Move bottom-right (diagonal)
        elif Dir == Bottom_Right:
            self.motorControl(1, 0)
            self.motorControl(2, -Speed)
            self.motorControl(3, -Speed)
            self.motorControl(4, 0)

        # Move bottom-left (diagonal)
        elif Dir == Bottom_Left:
            self.motorControl(1, -Speed)
            self.motorControl(2, 0)
            self.motorControl(3, 0)
            self.motorControl(4, -Speed)

        # Stop all motors
        elif Dir == Stop:
            for i in range(1, 5):
                self.motorControl(i, 0)

