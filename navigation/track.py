class TrackFollower:

    def __init__(self, car):

        self.car = car


        # ------------------------------------------
        # CAMERA ERROR
        # ------------------------------------------

        # Small errors should not cause corrections.
        self.deadband = 5


        # Larger deviation gets a stronger correction.
        self.strong_error = 18


        # ------------------------------------------
        # SPEEDS
        # ------------------------------------------

        self.learning_speed = 130

        self.fast_speed = 180


        self.learning_correction_speed = 110

        self.fast_correction_speed = 140


    def follow(
        self,
        error,
        lap=1
    ):
        """
        Follow the track using the camera patrol error.

        Negative error:
            track is toward one side.

        Positive error:
            track is toward the opposite side.

        IMPORTANT:
        If directions are reversed on the real robot,
        swap diagonal_forward_left/right below.
        """

        if lap <= 1:

            forward_speed = (
                self.learning_speed
            )

            correction_speed = (
                self.learning_correction_speed
            )

        else:

            forward_speed = (
                self.fast_speed
            )

            correction_speed = (
                self.fast_correction_speed
            )


        # ------------------------------------------
        # CENTERED
        # ------------------------------------------

        if abs(error) <= self.deadband:

            self.car.forward(
                forward_speed
            )

            return "straight"


        # ------------------------------------------
        # TRACK LEFT
        # ------------------------------------------

        if error < -self.deadband:

            self.car.diagonal_forward_left(
                correction_speed
            )

            return "correct_left"


        # ------------------------------------------
        # TRACK RIGHT
        # ------------------------------------------

        if error > self.deadband:

            self.car.diagonal_forward_right(
                correction_speed
            )

            return "correct_right"


        self.car.forward(
            forward_speed
        )

        return "straight"