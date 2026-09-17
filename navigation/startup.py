import time


class StartupDirectionDetector:
    """
    Determine the course direction from the blue start line.

    The vehicle remains stationary for the complete scan. Several
    observations are collected because one camera frame should not
    decide the direction of the whole run.

    We only ever look for BLUE. Orange and red sit close enough in
    hue that lighting can flip one into the other on the K210's
    fixed colour thresholds, so instead of trying to tell them
    apart we treat "blue confirmed" and "blue not confirmed" as the
    two outcomes - if blue is not seen, the course is assumed to be
    the other (orange) direction rather than actively detecting
    orange at all.
    """

    def __init__(
        self,
        link,
        min_width: int,
        min_height: int,
        min_pixels: int,
        min_votes: int,
        scan_ms: int,
        sample_delay_ms: int,
        blue_direction: str = "left",
        alt_direction: str = "right"
    ) -> None:
        """
        Store the startup colour detector configuration.

        Args:
            link: Connected K210Link.
            min_width: Minimum accepted blob width.
            min_height: Minimum accepted blob height.
            min_pixels: Minimum accepted blob pixel count. The K210
                already applies its own (looser) threshold before
                reporting anything at all - this is a stricter
                second filter on the ESP32 side.
            min_votes: Minimum observations required to confirm blue.
            scan_ms: Amount of time the car stays stationary.
            sample_delay_ms: Delay between observation cycles.
            blue_direction: Course direction when blue is confirmed.
            alt_direction: Course direction when blue is not seen.

        Returns:
            None.
        """

        self.link = link

        self.min_width = min_width
        self.min_height = min_height
        self.min_pixels = min_pixels

        self.min_votes = min_votes

        self.scan_ms = scan_ms
        self.sample_delay_ms = sample_delay_ms

        self.blue_direction = blue_direction
        self.alt_direction = alt_direction


    def _blue_seen(self) -> bool:
        """
        Poll the link once and check for a valid blue blob.

        Returns:
            True if blue was reported and clears the size filters.
        """

        found = self.link.poll()

        if not found or self.link.name != "blue":
            return False

        if self.link.w < self.min_width:
            return False

        if self.link.h < self.min_height:
            return False

        if self.link.pixels < self.min_pixels:
            return False

        return True


    def detect(self) -> str:
        """
        Scan for blue for the configured duration and pick a side.

        We never look for orange. Its hue sits close enough to red
        that lighting can flip the classification between the two,
        so instead of comparing blue against orange votes, blue
        alone must clear min_votes to be "confirmed" - anything
        else (including a genuine orange line) falls through to
        alt_direction.

        Returns:
            blue_direction if blue was confirmed, alt_direction
            otherwise.
        """

        self.link.set_mode(self.link.MODE_START)

        blue_votes = 0

        started_ms = time.ticks_ms()
        last_status_ms = started_ms

        print("")
        print("================================")
        print("STARTUP DIRECTION SCAN")
        print("================================")
        print("Car stationary, looking for BLUE only")
        print("BLUE FOUND ->", self.blue_direction.upper())
        print("BLUE NOT FOUND ->", self.alt_direction.upper())
        print("")

        while True:

            now = time.ticks_ms()

            elapsed = time.ticks_diff(
                now,
                started_ms
            )

            if elapsed >= self.scan_ms:
                break

            if self._blue_seen():

                blue_votes += 1


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
                    blue_votes
                )

                last_status_ms = now


            time.sleep_ms(
                self.sample_delay_ms
            )


        print("")
        print(
            "FINAL BLUE VOTES:",
            blue_votes
        )


        if blue_votes >= self.min_votes:

            print("BLUE CONFIRMED")
            print("COURSE DIRECTION:", self.blue_direction.upper())

            return self.blue_direction


        print("BLUE NOT CONFIRMED - ASSUMING ORANGE")
        print("COURSE DIRECTION:", self.alt_direction.upper())

        return self.alt_direction
