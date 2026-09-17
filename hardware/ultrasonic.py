import time
import libs.ultrasonic


class UltrasonicScanner:
    """
    Fixed forward-facing ultrasonic sensor.

    The ultrasonic is now a secondary sensor.
    It does not decide where the robot should drive.

    Its main job is to confirm that a physical wall
    or obstacle is close to the front of the robot.
    """

    def __init__(
        self,
        trig_pin=13,
        echo_pin=14
    ):

        self.sensor = libs.ultrasonic.ACB_Ultrasonic(
            trig_pin,
            echo_pin
        )


    def get_distance(self):
        """
        Return one raw ultrasonic reading.
        """

        return self.sensor.get_distance()


    def get_stable_distance(self, samples=3):
        """
        Take several readings and return the median.

        This helps reject occasional bad ultrasonic readings.
        """

        readings = []

        for _ in range(samples):

            distance = self.sensor.get_distance()

            if (
                distance > 0
                and distance != float('inf')
            ):
                readings.append(distance)

            time.sleep_ms(15)


        if not readings:
            return 999


        readings.sort()

        return readings[
            len(readings) // 2
        ]