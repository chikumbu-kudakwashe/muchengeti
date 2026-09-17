from machine import Pin, PWM


class Leds:
    """
    Left/right indicator LEDs.

    Used as turn signals: lit while the robot is committed to a
    corner or a traffic-pillar side-pass in that direction, off
    otherwise.
    """

    def __init__(
        self,
        left_pin=2,
        right_pin=12,
        freq=1000,
        on_duty=1023
    ):

        self.on_duty = on_duty

        self.left = PWM(
            Pin(left_pin),
            freq=freq,
            duty=0
        )

        self.right = PWM(
            Pin(right_pin),
            freq=freq,
            duty=0
        )


    def indicate(self, direction: str) -> None:
        """
        Light the LED for one side, turning the other off.

        Args:
            direction: "left", "right", or None/anything else to
                turn both off.

        Returns:
            None.
        """

        if direction == "left":

            self.left.duty(self.on_duty)
            self.right.duty(0)

        elif direction == "right":

            self.right.duty(self.on_duty)
            self.left.duty(0)

        else:

            self.clear()


    def clear(self) -> None:
        """
        Turn both indicator LEDs off.
        """

        self.left.duty(0)
        self.right.duty(0)
