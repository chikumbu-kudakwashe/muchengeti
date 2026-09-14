import time

import libs.ultrasonic
import libs.servo


class UltrasonicScanner:
    def __init__(
        self,
        trig_pin=13,
        echo_pin=14,
        servo_pin=25
    ):
        # Angles for checking the front and both sides.
        self.front_angle = 90
        self.right_angle = 0
        self.left_angle = 180

        # Reach position
       
        self.servo_settle_time = 0.20

       
        self.sensor = libs.ultrasonic.ACB_Ultrasonic(
            trig_pin,
            echo_pin
        )

    
        self.servo = libs.servo.Servo()
        self.servo.attach(servo_pin)

       
        self.servo.write(self.front_angle)

        time.sleep(0.2)


    def get_distance(self):
        """
        Get one distance reading from the ultrasonic sensor.
        """

        return self.sensor.get_distance()


    def get_stable_distance(self, samples=3):
        """
        Take a few readings and use the middle value.

        I do this because one ultrasonic reading can sometimes
        be wrong because of reflections or noise.
        """

        readings = []

        for _ in range(samples):
            distance = self.sensor.get_distance()

            # Ignore invalid or timeout readings.
            if (
                distance > 0
                and distance != float('inf')
            ):
                readings.append(distance)

            time.sleep(0.02)

        # If the sensor did not get any useful readings,
        # return a large distance so it means "nothing nearby".
        if not readings:
            return 999

        readings.sort()

        # Return the median reading.
        return readings[len(readings) // 2]


    def look_forward(self):
        """
        Point the ultrasonic sensor forward and check the distance.
        """

        self.servo.write(self.front_angle)
        time.sleep(self.servo_settle_time)

        return self.get_stable_distance()


    def look_right(self):
        """
        Turn the sensor to the right and check the distance.
        """

        self.servo.write(self.right_angle)
        time.sleep(self.servo_settle_time)

        return self.get_stable_distance()


    def look_left(self):
        """
        Turn the sensor to the left and check the distance.
        """

        self.servo.write(self.left_angle)
        time.sleep(self.servo_settle_time)

        return self.get_stable_distance()


    def scan_sides(self):
        """
        Check both sides and then put the sensor back
        in the forward position.
        """

        right_distance = self.look_right()
        left_distance = self.look_left()

        self.servo.write(self.front_angle)
        time.sleep(self.servo_settle_time)

        return left_distance, right_distance


    def scan_all(self):
        """
        Get front, left and right distances.

        This will be useful when I start deciding whether
        I am seeing a corner, obstacle or open path.
        """

        front_distance = self.look_forward()
        right_distance = self.look_right()
        left_distance = self.look_left()

        # Put the sensor back to the front when the scan is finished.
        self.servo.write(self.front_angle)
        time.sleep(self.servo_settle_time)

        return {
            "front": front_distance,
            "left": left_distance,
            "right": right_distance
        }