"""
Race support for main.py.

Holds everything that main.py's state machine needs but that is
not itself a state transition: distance/camera reading, traffic
sign scanning and sizing, corner pivoting, lap/finish timing, and
the turn-signal LEDs. main.py stays a plain "if state == X" loop
that reads/writes a Race instance instead of a page of helpers.
"""

import time

import config.settings as settings


def median(values: list) -> int:
    """
    Return the median integer from a list.

    Args:
        values: Numeric values.

    Returns:
        Median value or zero for an empty list.
    """

    if not values:
        return 0

    ordered = list(values)

    ordered.sort()

    count = len(ordered)

    middle = count // 2

    if count % 2 == 1:

        return ordered[middle]

    return (
        ordered[middle - 1]
        +
        ordered[middle]
    ) // 2


def is_valid_distance(distance: float) -> bool:
    """
    Check whether an ultrasonic value can be trusted.

    Args:
        distance: Distance returned by the ultrasonic sensor.

    Returns:
        True for a usable distance reading.
    """

    if distance is None:
        return False

    if distance <= 0:
        return False

    if distance >= settings.MAX_VALID_DISTANCE_CM:
        return False

    return True


class Race:
    """
    Shared state and helper logic for the main.py state machine.
    """

    def __init__(
        self,
        car,
        ultrasonic,
        traffic_detector,
        leds
    ):

        self.car = car
        self.ultrasonic = ultrasonic
        self.traffic_detector = traffic_detector
        self.leds = leds


        # ----------------------------------------------
        # RACE PROGRESS
        # ----------------------------------------------

        self.course_direction = settings.DEFAULT_TURN_DIRECTION

        self.total_turns = 0


        # ----------------------------------------------
        # ULTRASONIC
        # ----------------------------------------------

        self.front_distance = 999

        self.last_ultrasonic_ms = time.ticks_ms()


        # ----------------------------------------------
        # CORNER STATE
        # ----------------------------------------------

        self.active_corner_direction = None

        # Consecutive close-range frames with no traffic colour
        # detected. Requires several bad reads before a wall/corner
        # is committed to.
        self.wall_no_color_streak = 0

        self.turn_started_ms = 0

        self.turn_saw_close_wall = False

        self.corner_trim_started_ms = 0

        self.corner_recovery_started_ms = 0


        # ----------------------------------------------
        # TRAFFIC STATE
        # ----------------------------------------------

        self.active_traffic_color = None

        self.active_traffic_direction = None

        self.active_traffic_cx = settings.TRAFFIC_CAMERA_CENTER_X

        self.active_traffic_shift_ms = settings.TRAFFIC_SHIFT_MS_MIN

        self.traffic_shift_started_ms = 0

        self.traffic_pass_started_ms = 0

        self.traffic_recenter_started_ms = 0

        self.traffic_recenter_phase = 0

        self.traffic_lost_count = 0

        self.last_traffic_scan_ms = 0

        self.last_traffic_completed_ms = time.ticks_ms()


        # ----------------------------------------------
        # FINISH POSITION LEARNING
        # ----------------------------------------------

        self.run_started_ms = 0

        self.straight_started_ms = 0

        self.first_partial_straight_ms = None

        self.clean_straight_samples = []

        self.traffic_seen_on_current_straight = False

        self.finish_started_ms = 0

        self.finish_drive_ms = settings.FINISH_FORWARD_FALLBACK_MS


    # ============================================================
    # DISTANCE
    # ============================================================

    def update_front_distance(self) -> float:
        """
        Refresh the front ultrasonic reading at a controlled rate.

        Invalid readings are replaced with 999 rather than keeping
        an old close distance that could trigger another false
        corner.

        Returns:
            Current front distance in centimetres.
        """

        now = time.ticks_ms()

        if time.ticks_diff(
            now,
            self.last_ultrasonic_ms
        ) < settings.ULTRASONIC_INTERVAL_MS:

            return self.front_distance

        distance = self.ultrasonic.get_stable_distance()

        if is_valid_distance(distance):

            self.front_distance = distance

        else:

            self.front_distance = 999

        self.last_ultrasonic_ms = now

        return self.front_distance


    # ============================================================
    # TRAFFIC
    # ============================================================

    def scan_traffic_sign(self) -> object:
        """
        Check the camera for a red or green traffic pillar.

        Returns:
            Traffic-sign dictionary or None.
        """

        result = self.traffic_detector.detect()

        if result is None:
            return None

        print(
            "TRAFFIC:",
            result["color"].upper(),
            "PASS:",
            result["direction"].upper(),
            "W:",
            result["width"],
            "H:",
            result["height"],
            "AREA:",
            result["area"]
        )

        return result


    def lock_traffic(self, traffic: dict) -> None:
        """
        Store a confirmed pillar detection and signal its side.

        Args:
            traffic: Detection dictionary from scan_traffic_sign().

        Returns:
            None.
        """

        self.active_traffic_color = traffic["color"]
        self.active_traffic_direction = traffic["direction"]
        self.active_traffic_cx = traffic["cx"]

        self.traffic_seen_on_current_straight = True

        self.leds.indicate(self.active_traffic_direction)


    def compute_shift_ms(self, cx: int) -> int:
        """
        Size the sideways avoidance shift to how off-center a
        pillar is.

        A pillar close to the camera's center line is likely
        already close to the outer wall or the center obstacle and
        needs a smaller sideways move; one far off-center needs
        more clearance. Scales linearly between TRAFFIC_SHIFT_MS_MIN
        and _MAX using the blob's horizontal camera position
        (getCX).

        Args:
            cx: Horizontal camera position of the pillar blob.

        Returns:
            Shift duration in milliseconds.
        """

        offset = abs(
            cx - settings.TRAFFIC_CAMERA_CENTER_X
        )

        fraction = (
            offset
            /
            settings.TRAFFIC_CX_FULL_OFFSET_PX
        )

        if fraction > 1:
            fraction = 1

        return int(
            settings.TRAFFIC_SHIFT_MS_MIN
            +
            fraction
            *
            (
                settings.TRAFFIC_SHIFT_MS_MAX
                -
                settings.TRAFFIC_SHIFT_MS_MIN
            )
        )


    def shift_away_from_pillar(self, direction: str) -> None:
        """
        Steer toward the correct side of a traffic pillar.

        Red gives direction='right'.
        Green gives direction='left'.

        Uses a forward-diagonal move rather than a pure sideways
        strafe: strafe_left/strafe_right command all four wheels in
        the mixed-sign mecanum "X" pattern, which on this chassis
        does not behave as a clean lateral move (see hardware notes
        elsewhere - it has been observed spinning the robot instead
        of translating it, and inverted the intended side). The
        diagonal move only drives two wheels and keeps making
        forward progress, giving a gentler "lean" to one side
        instead of a full sideways hop or an in-place turn.

        Args:
            direction: Side on which the pillar must be passed.

        Returns:
            None.
        """

        if direction == "right":

            self.car.diagonal_forward_right(
                settings.TRAFFIC_SHIFT_SPEED
            )

        else:

            self.car.diagonal_forward_left(
                settings.TRAFFIC_SHIFT_SPEED
            )


    def shift_back_to_route(self, direction: str) -> None:
        """
        Undo the sideways lean used to pass a pillar.

        Args:
            direction: Original traffic-passing direction.

        Returns:
            None.
        """

        if direction == "right":

            self.car.diagonal_forward_left(
                settings.TRAFFIC_RECENTER_SPEED
            )

        else:

            self.car.diagonal_forward_right(
                settings.TRAFFIC_RECENTER_SPEED
            )


    def clear_traffic(self) -> None:
        """
        Reset traffic state after a pillar manoeuvre completes.
        """

        self.active_traffic_color = None
        self.active_traffic_direction = None

        self.traffic_lost_count = 0
        self.traffic_recenter_phase = 0

        self.last_traffic_completed_ms = time.ticks_ms()

        self.leds.clear()


    # ============================================================
    # CORNERS
    # ============================================================

    def drive_corner(self, direction: str, speed: int = None) -> None:
        """
        Pivot the car in place through a 90-degree track turn.

        The ultrasonic is fixed facing forward, so rotating in
        place sweeps it away from the old wall and toward the new
        straight. The CORNER_TURNING state watches that sweep to
        decide when the turn is done.

        Args:
            direction: "left" or "right".
            speed: Rotation speed. Defaults to CORNER_TURN_SPEED.

        Returns:
            None.
        """

        if speed is None:
            speed = settings.CORNER_TURN_SPEED

        if direction == "left":

            self.car.rotate_left(speed)

        else:

            self.car.rotate_right(speed)


    def lock_corner(self, direction: str) -> None:
        """
        Commit to a corner in the given direction and signal it.
        """

        self.active_corner_direction = direction

        self.leds.indicate(direction)


    def clear_corner(self) -> None:
        """
        Reset corner state after a turn completes.
        """

        self.active_corner_direction = None

        self.leds.clear()


    def current_lap(self) -> int:
        """
        Return the lap currently being driven.

        Returns:
            Lap number from 1 to TOTAL_LAPS.
        """

        lap = (
            self.total_turns
            // settings.TURNS_PER_LAP
        ) + 1

        if lap > settings.TOTAL_LAPS:
            lap = settings.TOTAL_LAPS

        return lap


    def count_completed_corner(self) -> None:
        """
        Count one completed physical 90-degree track corner.

        This is the only method that changes total_turns. Traffic
        manoeuvres never call this.

        Returns:
            None.
        """

        self.total_turns += 1

        turn_in_lap = (
            (self.total_turns - 1)
            %
            settings.TURNS_PER_LAP
        ) + 1

        lap_number = (
            (self.total_turns - 1)
            //
            settings.TURNS_PER_LAP
        ) + 1

        print("")
        print("================================")
        print("90 DEGREE TURN COMPLETE")
        print(
            "TOTAL:",
            self.total_turns,
            "/",
            settings.TOTAL_TURNS
        )
        print(
            "LAP:",
            lap_number,
            "TURN:",
            turn_in_lap,
            "/",
            settings.TURNS_PER_LAP
        )

        if (
            self.total_turns
            %
            settings.TURNS_PER_LAP
            ==
            0
        ):

            print(
                "LAP",
                lap_number,
                "COMPLETE"
            )

        print("================================")
        print("")


    # ============================================================
    # FINISH POSITION LEARNING
    # ============================================================

    def record_straight_before_corner(self) -> None:
        """
        Record straight-section timing for finish-position
        estimation.

        The first measurement is the time from the starting
        position to the first corner. Later clean straight sections
        give an estimate of a complete straight.

        Straights containing a traffic avoidance manoeuvre are
        ignored because the sideways movement changes their elapsed
        time.

        Returns:
            None.
        """

        now = time.ticks_ms()

        elapsed = time.ticks_diff(
            now,
            self.straight_started_ms
        )

        if self.total_turns == 0:

            if self.first_partial_straight_ms is None:

                self.first_partial_straight_ms = elapsed

                print(
                    "START OFFSET LEARNED:",
                    self.first_partial_straight_ms,
                    "ms"
                )

            return

        if self.traffic_seen_on_current_straight:

            print(
                "STRAIGHT TIMING IGNORED - TRAFFIC MANOEUVRE"
            )

            return

        if elapsed < 200:

            return

        self.clean_straight_samples.append(elapsed)

        # Keep the most recent values only.
        if len(self.clean_straight_samples) > 8:

            self.clean_straight_samples.pop(0)

        print(
            "CLEAN STRAIGHT:",
            elapsed,
            "ms"
        )


    def estimate_finish_drive_time(self) -> int:
        """
        Estimate how far to drive after the final corner.

        After the last turn we are back on the straight containing
        the original start. A learned full-straight time minus the
        original start-to-first-corner time gives an approximate
        corner-to-start time.

        Returns:
            Forward-driving time in milliseconds.
        """

        if self.first_partial_straight_ms is None:

            return settings.FINISH_FORWARD_FALLBACK_MS

        full_straight_ms = median(
            self.clean_straight_samples
        )

        if full_straight_ms <= 0:

            return settings.FINISH_FORWARD_FALLBACK_MS

        estimate = (
            full_straight_ms
            -
            self.first_partial_straight_ms
        )

        if estimate < 0:

            estimate = 0

        if estimate > settings.FINISH_FORWARD_MAX_MS:

            estimate = settings.FINISH_FORWARD_MAX_MS

        return estimate
