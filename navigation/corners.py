import time


class CornerDetector:
    """
    Detects which mat corner-line color (per WRO rule 13.9, orange
    and blue) is showing at the upcoming corner, and locks a turn
    direction from it.

    This is deliberately separate from navigation/vision.py's
    PillarVision: mat corner-lines decide which way to turn, while
    red/green traffic pillars (rule 9.19) decide which side to pass
    an obstacle on. Mixing the two up would send the robot the
    wrong way around the whole track.
    """

    def __init__(
        self,
        camera,
        orange_index,
        blue_index,
        pixels_threshold,
        area_threshold,
        orange_direction,
        blue_direction,
        confirmations_required=3,
        min_width=10,
        min_height=10,
        min_area=150
    ):

        self.camera = camera

        self.orange_index = orange_index
        self.blue_index = blue_index

        self.pixels_threshold = pixels_threshold
        self.area_threshold = area_threshold

        self.orange_direction = orange_direction
        self.blue_direction = blue_direction

        self.confirmations_required = confirmations_required

        self.min_width = min_width
        self.min_height = min_height
        self.min_area = min_area

        self.reset()


    def reset(self):
        """
        Call this before searching for the next corner. Clears any
        previous lock so a new corner starts from a clean slate.
        """

        self.next_color = "orange"

        self.orange_count = 0
        self.blue_count = 0

        self.locked_color = None
        self.locked_direction = None

        self.observation = None


    def _valid_size(self):

        width = self.camera.getW
        height = self.camera.getH

        area = width * height

        if width < self.min_width:
            return False

        if height < self.min_height:
            return False

        if area < self.min_area:
            return False

        return True


    def _lock(self, color, direction):

        self.locked_color = color
        self.locked_direction = direction

        self.observation = {
            "color": color,
            "direction": direction,
            "cx": self.camera.getCX,
            "width": self.camera.getW,
            "height": self.camera.getH,
            "timestamp": time.ticks_ms()
        }


    def update(self):
        """
        Check one color per call and alternate to the other next
        time. Returns the locked direction once confident, or None
        while still searching.

        Alternating colors (instead of checking both every call)
        keeps this to one camera mode switch per call, the same
        pattern navigation/vision.PillarVision uses for red/green.
        """

        if self.locked_direction is not None:
            return self.locked_direction

        if self.next_color == "orange":

            detected = self.camera.color_recognize(
                self.orange_index,
                self.pixels_threshold,
                self.area_threshold
            )

            self.next_color = "blue"

            if detected and self._valid_size():

                self.orange_count += 1
                self.blue_count = 0

                if self.orange_count >= self.confirmations_required:

                    self._lock("orange", self.orange_direction)

                    return self.locked_direction

            else:

                self.orange_count = 0

        else:

            detected = self.camera.color_recognize(
                self.blue_index,
                self.pixels_threshold,
                self.area_threshold
            )

            self.next_color = "orange"

            if detected and self._valid_size():

                self.blue_count += 1
                self.orange_count = 0

                if self.blue_count >= self.confirmations_required:

                    self._lock("blue", self.blue_direction)

                    return self.locked_direction

            else:

                self.blue_count = 0

        return None
