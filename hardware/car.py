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