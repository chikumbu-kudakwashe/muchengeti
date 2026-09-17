import time


class StartupDirectionDetector:
    """
    Determine the course direction from the blue and orange lines.

    The vehicle remains stationary for the complete scan. Several
    observations are collected because one camera frame should not
    decide the direction of the whole run.

    Blue means left.
    Orange means right.
    """

    def __init__(
        self,
        camera,
        blue_index: int,
        orange_index: int,
        pixels_threshold: int,
        area_threshold: int,
        min_width: int,
        min_height: int,
        min_area: int,
        min_votes: int,
        vote_margin: int,
        scan_ms: int,
        sample_delay_ms: int
    ) -> None:
        """
        Store the startup colour detector configuration.

        Args:
            camera: Initialised ACB_Canmv camera.
            blue_index: K210 colour index for blue.
            orange_index: K210 colour index for orange.
            pixels_threshold: Minimum camera pixel threshold.
            area_threshold: Minimum camera area threshold.
            min_width: Minimum accepted blob width.
            min_height: Minimum accepted blob height.
            min_area: Minimum accepted width x height.
            min_votes: Minimum observations required for confidence.
            vote_margin: Preferred lead between winning and losing colour.
            scan_ms: Amount of time the car stays stationary.
            sample_delay_ms: Delay between observation cycles.

        Returns:
            None.
        """

        self.camera = camera

        self.blue_index = blue_index
        self.orange_index = orange_index

        self.pixels_threshold = pixels_threshold
        self.area_threshold = area_threshold

        self.min_width = min_width
        self.min_height = min_height
        self.min_area = min_area

        self.min_votes = min_votes
        self.vote_margin = vote_margin

        self.scan_ms = scan_ms
        self.sample_delay_ms = sample_delay_ms


    def _read_colour(self, index: int) -> dict:
        """
        Read one K210 colour class and return its blob information.

        A small blob is treated as noise. The lower thresholds make
        the detector tolerant to dim lighting while the size check
        stops isolated coloured pixels from becoming valid votes.

        Args:
            index: K210 colour-recognition index.

        Returns:
            Dictionary containing detection information.
        """

        detected = self.camera.color_recognize(
            index,
            self.pixels_threshold,
            self.area_threshold
        )

        if not detected:
            return {
                "detected": False,
                "width": 0,
                "height": 0,
                "area": 0
            }

        width = self.camera.getW
        height = self.camera.getH
        area = width * height

        if width < self.min_width:
            return {
                "detected": False,
                "width": width,
                "height": height,
                "area": area
            }

        if height < self.min_height:
            return {
                "detected": False,
                "width": width,
                "height": height,
                "area": area
            }

        if area < self.min_area:
            return {
                "detected": False,
                "width": width,
                "height": height,
                "area": area
            }

        return {
            "detected": True,
            "width": width,
            "height": height,
            "area": area
        }


    def detect(self, fallback_direction: str) -> str:
        """
        Scan blue and orange for ten seconds and select the direction.

        The detector uses a voting system rather than trusting one
        frame. If both colours are visible in one cycle, the larger
        valid blob receives the vote.

        Args:
            fallback_direction: Direction used if the result is tied.

        Returns:
            "left" when blue wins or "right" when orange wins.
        """

        blue_votes = 0
        orange_votes = 0

        blue_area_total = 0
        orange_area_total = 0

        started_ms = time.ticks_ms()
        last_status_ms = started_ms

        print("")
        print("================================")
        print("STARTUP DIRECTION SCAN")
        print("================================")
        print("Car stationary for 10 seconds")
        print("BLUE = LEFT")
        print("ORANGE = RIGHT")
        print("")

        while True:

            now = time.ticks_ms()

            elapsed = time.ticks_diff(
                now,
                started_ms
            )

            if elapsed >= self.scan_ms:
                break

            blue = self._read_colour(
                self.blue_index
            )

            orange = self._read_colour(
                self.orange_index
            )

            # If both colours are reported in the same cycle we use
            # the larger blob instead of giving both a vote.
            if (
                blue["detected"]
                and
                orange["detected"]
            ):

                if blue["area"] >= orange["area"]:

                    blue_votes += 1
                    blue_area_total += blue["area"]

                else:

                    orange_votes += 1
                    orange_area_total += orange["area"]


            elif blue["detected"]:

                blue_votes += 1
                blue_area_total += blue["area"]


            elif orange["detected"]:

                orange_votes += 1
                orange_area_total += orange["area"]


            if time.ticks_diff(
                now,
                last_status_ms
            ) >= 1000:

                remaining = (
                    self.scan_ms
                    - elapsed
                ) // 1000

                print(
                    "SCAN:",
                    remaining,
                    "s | BLUE:",
                    blue_votes,
                    "| ORANGE:",
                    orange_votes
                )

                last_status_ms = now


            time.sleep_ms(
                self.sample_delay_ms
            )


        print("")
        print(
            "FINAL VOTES | BLUE:",
            blue_votes,
            "| ORANGE:",
            orange_votes
        )


        # Clear result with our preferred confidence margin.
        if (
            blue_votes >= self.min_votes
            and
            blue_votes
            >=
            orange_votes + self.vote_margin
        ):

            print("START LINE: BLUE")
            print("COURSE DIRECTION: LEFT")

            return "left"


        if (
            orange_votes >= self.min_votes
            and
            orange_votes
            >=
            blue_votes + self.vote_margin
        ):

            print("START LINE: ORANGE")
            print("COURSE DIRECTION: RIGHT")

            return "right"


        # If there is no full confidence margin but one colour has
        # still been seen more often, use the stronger observation.
        if (
            blue_votes >= self.min_votes
            and
            blue_votes > orange_votes
        ):

            print("LOW CONFIDENCE BLUE")
            print("COURSE DIRECTION: LEFT")

            return "left"


        if (
            orange_votes >= self.min_votes
            and
            orange_votes > blue_votes
        ):

            print("LOW CONFIDENCE ORANGE")
            print("COURSE DIRECTION: RIGHT")

            return "right"


        # Area gives us one last useful comparison in a close vote.
        if (
            blue_area_total > orange_area_total
            and
            blue_area_total > 0
        ):

            print("CLOSE VOTE - BLUE HAD LARGER BLOBS")

            return "left"


        if (
            orange_area_total > blue_area_total
            and
            orange_area_total > 0
        ):

            print("CLOSE VOTE - ORANGE HAD LARGER BLOBS")

            return "right"


        print(
            "NO RELIABLE START COLOUR - FALLBACK:",
            fallback_direction.upper()
        )

        return fallback_direction