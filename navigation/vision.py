import time


class PillarVision:

    def __init__(
        self,
        camera,
        red_index=1,
        green_index=2,
        pixels_threshold=200,
        area_threshold=200
    ):

        self.camera = camera

        self.red_index = red_index
        self.green_index = green_index

        self.pixels_threshold = pixels_threshold
        self.area_threshold = area_threshold


        # ------------------------------------------
        # SIZE FILTER
        # ------------------------------------------
        #
        # These are CAMERA pixel dimensions.
        # They are NOT centimetres.
        #
        # Tune these using the real traffic pillars.

        self.min_width = 12
        self.min_height = 20
        self.min_area = 300


        # ------------------------------------------
        # CONFIRMATION
        # ------------------------------------------

        self.confirmations_required = 3

        self.red_count = 0
        self.green_count = 0


        # ------------------------------------------
        # MEMORY
        # ------------------------------------------

        self.memory_ms = 2000

        self.last_color = None
        self.last_seen = 0

        self.cx = 0
        self.cy = 0

        self.width = 0
        self.height = 0


        # Alternate red and green searches.
        self.next_color = "red"


    # --------------------------------------------------
    # VALIDATE SIZE
    # --------------------------------------------------

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


    # --------------------------------------------------
    # SAVE DETECTION
    # --------------------------------------------------

    def _save_detection(self, color):

        self.last_color = color
        self.last_seen = time.ticks_ms()

        self.cx = self.camera.getCX
        self.cy = self.camera.getCY

        self.width = self.camera.getW
        self.height = self.camera.getH


    # --------------------------------------------------
    # CAMERA UPDATE
    # --------------------------------------------------

    def update(self):
        """
        Check one colour per call.

        Returns:
            "red"
            "green"
            None
        """

        # ------------------------------------------
        # RED
        # ------------------------------------------

        if self.next_color == "red":

            detected = self.camera.color_recognize(
                self.red_index,
                self.pixels_threshold,
                self.area_threshold
            )

            self.next_color = "green"


            if detected and self._valid_size():

                self.red_count += 1
                self.green_count = 0

                print(
                    "RED candidate",
                    "count:", self.red_count,
                    "CX:", self.camera.getCX,
                    "W:", self.camera.getW,
                    "H:", self.camera.getH
                )


                if self.red_count >= self.confirmations_required:

                    self._save_detection("red")

                    self.red_count = 0
                    self.green_count = 0

                    print("RED CONFIRMED")

                    return "red"

            else:

                self.red_count = 0


        # ------------------------------------------
        # GREEN
        # ------------------------------------------

        else:

            detected = self.camera.color_recognize(
                self.green_index,
                self.pixels_threshold,
                self.area_threshold
            )

            self.next_color = "red"


            if detected and self._valid_size():

                self.green_count += 1
                self.red_count = 0

                print(
                    "GREEN candidate",
                    "count:", self.green_count,
                    "CX:", self.camera.getCX,
                    "W:", self.camera.getW,
                    "H:", self.camera.getH
                )


                if self.green_count >= self.confirmations_required:

                    self._save_detection("green")

                    self.green_count = 0
                    self.red_count = 0

                    print("GREEN CONFIRMED")

                    return "green"

            else:

                self.green_count = 0


        return None


    # --------------------------------------------------
    # RECENT PILLAR
    # --------------------------------------------------

    def get_recent(self):

        if self.last_color is None:
            return None


        age = time.ticks_diff(
            time.ticks_ms(),
            self.last_seen
        )


        if age > self.memory_ms:

            self.clear()

            return None


        return self.last_color


    # --------------------------------------------------
    # CLEAR
    # --------------------------------------------------

    def clear(self):

        self.last_color = None

        self.red_count = 0
        self.green_count = 0

        self.cx = 0
        self.cy = 0

        self.width = 0
        self.height = 0