class TrafficColorDetector:
    """
    Detect red and green WRO traffic pillars.

    Red means the vehicle passes on the right.
    Green means the vehicle passes on the left.

    The K210 already picks the strongest blob among the colours
    allowed by its current mode and reports it by name, so this
    class only has to put the link in MODE_TRAFFIC and translate
    that one report into a pass side.
    """

    def __init__(
        self,
        link,
        min_width: int = 5,
        min_height: int = 5,
        min_pixels: int = 40,
        confirmations: int = 1
    ) -> None:
        """
        Configure the traffic-pillar detector.

        Args:
            link: Connected K210Link.
            min_width: Minimum accepted blob width.
            min_height: Minimum accepted blob height.
            min_pixels: Minimum accepted blob pixel count. The K210
                already applies its own (looser) threshold before
                reporting anything at all - this is a stricter
                second filter on the ESP32 side.
            confirmations: Number of repeated detections required.

        Returns:
            None.
        """

        self.link = link

        self.min_width = min_width
        self.min_height = min_height
        self.min_pixels = min_pixels

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
        Check whether the current link blob is larger than noise.

        Returns:
            True when the current blob is usable.
        """

        if self.link.w < self.min_width:
            return False

        if self.link.h < self.min_height:
            return False

        if self.link.pixels < self.min_pixels:
            return False

        return True


    def detect(self) -> object:
        """
        Check for a red or green pillar.

        Returns:
            Traffic-sign dictionary or None.
        """

        self.link.set_mode(self.link.MODE_TRAFFIC)

        found = self.link.poll()

        if not found or self.link.name not in ("red", "green"):

            self.reset()

            return None

        if not self._valid_blob():

            self.reset()

            return None

        color = self.link.name
        direction = "right" if color == "red" else "left"

        result = {
            "color": color,
            "direction": direction,
            "width": self.link.w,
            "height": self.link.h,
            "area": self.link.pixels,
            "cx": self.link.cx,
            "cy": self.link.cy
        }

        if color == "red":

            self.red_count += 1
            self.green_count = 0

            if self.red_count >= self.confirmations:

                self.reset()

                return result

        else:

            self.green_count += 1
            self.red_count = 0

            if self.green_count >= self.confirmations:

                self.reset()

                return result

        return None
