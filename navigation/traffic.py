import time


class TrafficColorDetector:
    """
    Detect red and green WRO traffic pillars.

    Red means the vehicle passes on the right.
    Green means the vehicle passes on the left.

    The detector only handles colour recognition. Motor movement
    remains in main.py so one state machine controls the car.
    """

    def __init__(
        self,
        cam,
        red_index: int = 1,
        green_index: int = 2,
        pixels_threshold: int = 60,
        area_threshold: int = 60,
        min_width: int = 5,
        min_height: int = 5,
        min_area: int = 40,
        confirmations: int = 1
    ) -> None:
        """
        Configure the traffic-pillar detector.

        Args:
            cam: Initialised ACB_Canmv camera.
            red_index: K210 colour index for red.
            green_index: K210 colour index for green.
            pixels_threshold: Camera pixel threshold.
            area_threshold: Camera area threshold.
            min_width: Minimum accepted blob width.
            min_height: Minimum accepted blob height.
            min_area: Minimum accepted width x height.
            confirmations: Number of repeated detections required.

        Returns:
            None.
        """

        self.cam = cam

        self.red_index = red_index
        self.green_index = green_index

        self.pixels_threshold = pixels_threshold
        self.area_threshold = area_threshold

        self.min_width = min_width
        self.min_height = min_height
        self.min_area = min_area

        self.confirmations = confirmations

        self.red_count = 0
        self.green_count = 0


    def reset(self) -> None:
        """
        Clear all temporary traffic-sign confirmations.

        Returns:
            None.
        """

        self.red_count = 0
        self.green_count = 0


    def _valid_blob(self) -> bool:
        """
        Check whether the current camera blob is larger than noise.

        Returns:
            True when the current blob is usable.
        """

        width = self.cam.getW
        height = self.cam.getH

        area = width * height

        if width < self.min_width:
            return False

        if height < self.min_height:
            return False

        if area < self.min_area:
            return False

        return True


    def _read_colour(
        self,
        index: int,
        colour: str,
        direction: str
    ) -> object:
        """
        Read one traffic-sign colour.

        Args:
            index: K210 colour index.
            colour: Name stored in the returned result.
            direction: Side used to pass this pillar.

        Returns:
            Detection dictionary or None.
        """

        found = self.cam.color_recognize(
            index,
            self.pixels_threshold,
            self.area_threshold
        )

        if not found:
            return None

        if not self._valid_blob():
            return None

        width = self.cam.getW
        height = self.cam.getH

        return {
            "color": colour,
            "direction": direction,
            "width": width,
            "height": height,
            "area": width * height,
            "cx": self.cam.getCX,
            "cy": self.cam.getCY
        }


    def detect(self) -> object:
        """
        Check red and green and return the strongest valid pillar.

        When both colours are seen, the larger blob is selected.
        The detection is then required to meet the configured
        confirmation count.

        Returns:
            Traffic-sign dictionary or None.
        """

        red = self._read_colour(
            self.red_index,
            "red",
            "right"
        )

        time.sleep_ms(15)

        green = self._read_colour(
            self.green_index,
            "green",
            "left"
        )


        if (
            red is None
            and
            green is None
        ):

            self.reset()

            return None


        if (
            red is not None
            and
            green is not None
        ):

            if red["area"] >= green["area"]:
                selected = red
            else:
                selected = green


        elif red is not None:

            selected = red


        else:

            selected = green


        if selected["color"] == "red":

            self.red_count += 1
            self.green_count = 0

            if self.red_count >= self.confirmations:

                self.reset()

                return selected


        else:

            self.green_count += 1
            self.red_count = 0

            if self.green_count >= self.confirmations:

                self.reset()

                return selected


        return None