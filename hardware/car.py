import libs.ACB_SmartCar_V2


class Car:
    def __init__(self):
        self.driver = libs.ACB_SmartCar_V2.ACB_SmartCar_V2()

        # Default Speeds
        self.forward_speed = 150
        self.reverse_speed = 150
        self.turn_speed = 160
        self.strafe_speed = 150

        self.stop()


    def stop(self):
        """
        Stop all four motors.
        """
        self.driver.Move(
            self.driver.Stop,
            0
        )


    def forward(self, speed=None):
        """
        Move straight forward.
        """
        if speed is None:
            speed = self.forward_speed

        self.driver.Move(
            self.driver.Forward,
            speed
        )


    def backward(self, speed=None):
        """
        Move straight backwards.
        """
        if speed is None:
            speed = self.reverse_speed

        self.driver.Move(
            self.driver.Backward,
            speed
        )


    def strafe_left(self, speed=None):
        """
        Move sideways to the left using the mecanum wheels.
        """
        if speed is None:
            speed = self.strafe_speed

        self.driver.Move(
            self.driver.Move_Left,
            speed
        )


    def strafe_right(self, speed=None):
        """
        Move sideways to the right using the mecanum wheels.
        """
        if speed is None:
            speed = self.strafe_speed

        self.driver.Move(
            self.driver.Move_Right,
            speed
        )


    def rotate_left(self, speed=None):
        """
        Rotate the whole car counter-clockwise.
        """
        if speed is None:
            speed = self.turn_speed

        self.driver.Move(
            self.driver.Contrarotate,
            speed
        )


    def rotate_right(self, speed=None):
        """
        Rotate the whole car clockwise.
        """
        if speed is None:
            speed = self.turn_speed

        self.driver.Move(
            self.driver.Clockwise,
            speed
        )


    def corner_left(self, speed=None, inner_ratio=0.3):
        """
        Drive a forward-left arc instead of pivoting in place.

        Left side (inner wheels) runs slower, right side (outer
        wheels) runs at full speed, both still moving forward.
        This uses the driver's per-motor motorControl() directly,
        because Move() only exposes fixed presets (forward, strafe,
        pivot, diagonals) and has no arc/differential preset.

        Motor sides come from how the vendor driver itself wires
        Clockwise/Contrarotate in ACB_SmartCar_V2.Move(): motors 1
        and 2 move together as the left side, 3 and 4 as the right
        side.
        """
        if speed is None:
            speed = self.forward_speed

        inner_speed = speed * inner_ratio

        self.driver.motorControl(1, inner_speed)
        self.driver.motorControl(2, inner_speed)
        self.driver.motorControl(3, speed)
        self.driver.motorControl(4, speed)


    def corner_right(self, speed=None, inner_ratio=0.3):
        """
        Drive a forward-right arc instead of pivoting in place.

        Right side (inner wheels) runs slower, left side (outer
        wheels) runs at full speed, both still moving forward.
        See corner_left() for why motorControl() is used directly.
        """
        if speed is None:
            speed = self.forward_speed

        inner_speed = speed * inner_ratio

        self.driver.motorControl(1, speed)
        self.driver.motorControl(2, speed)
        self.driver.motorControl(3, inner_speed)
        self.driver.motorControl(4, inner_speed)


    def diagonal_forward_left(self, speed=None):
        """
        Move diagonally forward and left.
        """
        if speed is None:
            speed = self.forward_speed

        self.driver.Move(
            self.driver.Top_Left,
            speed
        )


    def diagonal_forward_right(self, speed=None):
        """
        Move diagonally forward and right.
        """
        if speed is None:
            speed = self.forward_speed

        self.driver.Move(
            self.driver.Top_Right,
            speed
        )


    def diagonal_backward_left(self, speed=None):
        """
        Move diagonally backwards and left.
        """
        if speed is None:
            speed = self.reverse_speed

        self.driver.Move(
            self.driver.Bottom_Left,
            speed
        )


    def diagonal_backward_right(self, speed=None):
        """
        Move diagonally backwards and right.
        """
        if speed is None:
            speed = self.reverse_speed

        self.driver.Move(
            self.driver.Bottom_Right,
            speed
        )