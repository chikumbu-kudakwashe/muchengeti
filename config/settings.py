"""
Muchengeti runtime configuration.

Values in this file are kept separate from the navigation logic so
we can tune the robot on the real competition mat without changing
the state machine.
"""


# ============================================================
# FIELD
# ============================================================

# Zimbabwe Nationals practice / competition field.
MAT_SIZE_CM = 200

# Width of the driving lane the car travels along (outer wall to
# the center obstacle). Used as a sanity ceiling on how far the car
# is allowed to shift sideways when avoiding a traffic pillar - see
# SIDESTEP SIZING below.
TRACK_LANE_WIDTH_CM = 70


# ============================================================
# STARTUP DIRECTION SCAN
# ============================================================

# The robot must remain stationary while it determines whether
# the course direction is based on the blue or orange line.
STARTUP_SCAN_MS = 10000

# Small pause between complete blue/orange observations.
STARTUP_SAMPLE_DELAY_MS = 40


# ============================================================
# COURSE DIRECTION
# ============================================================

# Blue tells us to take the track corners to the left.
BLUE_TURN_DIRECTION = "left"

# Orange tells us to take the track corners to the right.
ORANGE_TURN_DIRECTION = "right"

# Used only when the startup scan cannot make a clear decision.
# This should be changed during testing if required.
DEFAULT_TURN_DIRECTION = "left"


# ============================================================
# K210 LINK
# ============================================================
#
# The K210 now runs our own text-protocol vision firmware (see
# libs/k210_link.py and the K210-side main.py/README_K210.txt)
# instead of the original ACEBOTT binary packet firmware. Colours
# are identified by name over UART, not by index, and blob-size
# filtering happens on the K210 itself (PIXELS_THRESHOLD/
# AREA_THRESHOLD in the K210's main.py) before anything is even
# reported - the MIN_WIDTH/MIN_HEIGHT/MIN_PIXELS settings below are
# just a stricter second filter applied on the ESP32 side.
#
# These are the same physical UART pins the old ACB_Canmv camera
# used (labelled SDA/SCL there, which was a misnomer - they were
# always UART rx/tx).
# ============================================================

K210_RX_PIN = 21
K210_TX_PIN = 22
K210_BAUD = 115200


# ============================================================
# STARTUP BLUE FILTERING
# ============================================================
#
# These values are deliberately permissive. We do not want to
# reject the line just because the lighting has made it darker or
# lighter than expected.
# ============================================================

START_COLOR_MIN_WIDTH = 4
START_COLOR_MIN_HEIGHT = 3
START_COLOR_MIN_PIXELS = 20

# Blue must be seen at least this many times during the scan to be
# confirmed. Not seeing it is treated as the orange/alt direction -
# we no longer actively look for orange (see navigation/startup.py).
START_COLOR_MIN_VOTES = 2


# ============================================================
# TRAFFIC SIGN FILTERING
# ============================================================

TRAFFIC_MIN_WIDTH = 5

# The orange/red corner-direction line painted on the mat is flat
# on the ground, so the camera sees it as a short, wide blob - a
# real pillar is a standing rectangular block and should read
# taller. Raising this above pure noise-rejection height is meant
# to tell the two apart, BUT 30 turned out to also reject genuine
# GREEN pillars until they were nearly passed (too strict). Backed
# off to a gentler value - use tests/traffic_calibration.py to read
# real width/height/pixels for the mat line vs each pillar colour
# on your camera and set this from actual numbers instead of a
# guess.
TRAFFIC_MIN_HEIGHT = 15

TRAFFIC_MIN_PIXELS = 40

# We currently allow one good observation to lock a pillar.
# Raise this to 2 if false detections become common.
TRAFFIC_CONFIRMATIONS = 1


# ============================================================
# SPEEDS
# ============================================================
#
# ACEBOTT motor commands use 0..255.
#
# The open straight is the Time Attack section, so we use the
# maximum command there.
# ============================================================

DRIVE_SPEED = 180

# Once we are close to something we slow down because a camera
# classification can take a few hundred milliseconds.
CLASSIFICATION_SPEED = 150

CORNER_APPROACH_SPEED = 150
CORNER_TURN_SPEED = 120
CORNER_EXIT_SPEED = 150

TRAFFIC_APPROACH_SPEED = 150

# Speed for the diagonal-forward lean used to pass a pillar (see
# Race.shift_away_from_pillar/shift_back_to_route) - a gentle lean
# to one side while still driving forward, not a sideways strafe or
# an in-place turn.
TRAFFIC_SHIFT_SPEED = 110
TRAFFIC_RECENTER_SPEED = 110

TRAFFIC_PASS_SPEED = 170

FINISH_SPEED = 180

BACKUP_SPEED = 130


# ============================================================
# WALL / CORNER DISTANCES
# ============================================================

MAX_VALID_DISTANCE_CM = 300

# At this distance we stop treating the straight as completely
# clear and determine whether the object is a pillar or wall.
BOUNDARY_CLASSIFY_CM = 70

# Physical corner manoeuvre starts here.
TURN_TRIGGER_CM = 28
# Last-resort collision protection.
EMERGENCY_CM = 9

# A single missed colour read at BOUNDARY_CLASSIFY_CM must not be
# enough to commit to a wall/corner - that is an irreversible 90
# degree turn, and this mat has pillars close enough together that
# one bad frame could otherwise turn the robot straight into one.
# This many consecutive close-range "no colour" reads are required
# first.
WALL_CONFIRM_COUNT = 3

# Keep re-checking for a pillar while approaching what we believe
# is the wall, down to this distance. A closer, larger blob is far
# more reliable than the original distant classification read, so
# a misclassified wall can still be caught and corrected here.
WALL_RECHECK_MIN_CM = 20


# ============================================================
# TURN COMPLETION
# ============================================================

# A real turn cannot finish before this period has elapsed.
TURN_MIN_MS = 400

# Stage 1 of the two-stage pivot-release check: confirm the
# ultrasonic has actually swept close past the old wall before we
# start looking for it to open back up. Without this, a turn that
# starts with the wall already somewhat open could release itself
# immediately.
TURN_WALL_CLOSE_CM = 20

# Stage 2: once the close wall has been confirmed, the turn is
# considered released once the reading grows beyond this distance.
TURN_CLEAR_DISTANCE_CM = 90 #45

# Prevent a bad ultrasonic reading from keeping the motors in a
# turn forever.
TURN_TIMEOUT_MS = 1600

# Short final pivot after the wall is seen to release. The
# ultrasonic beam is wide enough that "released" is detected a
# little before the car has actually reached 90 degrees, so this
# trims the remaining few degrees at a gentler speed for a more
# accurate finish.
TURN_TRIM_MS = 120
TURN_TRIM_SPEED = 110

# Continue forward briefly after each corner.
CORNER_RECOVERY_MS = 280


# ============================================================
# TRAFFIC PILLAR
# ============================================================

# Begin the avoidance lean once the pillar is this close.
TRAFFIC_PASS_TRIGGER_CM = 40

# ------------------------------------------------------------
# SIDESTEP SIZING
# ------------------------------------------------------------
#
# Pillars on this mat are not all the same distance into the lane
# - some sit close to the outer wall, others sit further toward
# the center obstacle. A single fixed lean duration is either too
# much or too little depending on where the pillar actually is, so
# it is scaled by how far off-center the pillar's camera blob
# (getCX) is at the moment we commit to passing it.
#
# CALIBRATE ON THE REAL CAMERA: TRAFFIC_CAMERA_CENTER_X should be
# the getCX reading for a pillar dead-center in frame, and
# TRAFFIC_CX_FULL_OFFSET_PX the offset (in the same units) at
# which the pillar is already at the edge of the lane.
#
# TRAFFIC_SHIFT_MS_MAX must never let the car drift further
# sideways than the lane actually allows (TRACK_LANE_WIDTH_CM,
# ~70cm) - overshooting that turns a pillar dodge into a wall hit
# on the other side of the lane. This is now a forward-diagonal
# lean (Race.shift_away_from_pillar), not a sideways strafe, so it
# also keeps making forward progress the whole time - to calibrate,
# time how many centimetres it drifts sideways over a fixed known
# duration at TRAFFIC_SHIFT_SPEED (mark the floor, measure the
# sideways offset only), then set MAX so the worst case stays well
# under half the lane width.

TRAFFIC_CAMERA_CENTER_X = 160

TRAFFIC_CX_FULL_OFFSET_PX = 80

TRAFFIC_SHIFT_MS_MIN = 270
TRAFFIC_SHIFT_MS_MAX = 500

# We do not look for the end of a pillar immediately.
TRAFFIC_MIN_PASS_MS = 450

# Safety limit in case the camera never reports it as gone.
TRAFFIC_MAX_PASS_MS = 1700

TRAFFIC_LOST_CONFIRMATIONS = 2

# Do not immediately rediscover the pillar we just passed - it can
# still be at the edge of the camera frame right after RECENTER.
# This mat places pillars close together on the same straight, so
# this must be short enough to still catch the next one in time
# rather than a long blanket cooldown.
TRAFFIC_COOLDOWN_MS = 300

# After undoing the sideways shift, drive straight for this long
# before declaring the pillar manoeuvre complete.
#
# The new K210 firmware only reports colour blobs - it dropped
# line-following (visual_patrol), so there is no camera signal left
# to confirm we are actually back at track center. This is a plain
# timed forward burst, same as the shift-out/shift-back timing.
RECENTER_FORWARD_MS = 220

# Camera scan interval while travelling on the straight.
TRAFFIC_SCAN_INTERVAL_MS = 250


# ============================================================
# ULTRASONIC
# ============================================================

ULTRASONIC_INTERVAL_MS = 80


# ============================================================
# INDICATOR LEDS
# ============================================================

LED_LEFT_PIN = 2
LED_RIGHT_PIN = 12

LED_PWM_FREQ = 1000


# ============================================================
# RACE
# ============================================================

TURNS_PER_LAP = 4
TOTAL_LAPS = 3

TOTAL_TURNS = (
    TURNS_PER_LAP
    * TOTAL_LAPS
)


# ============================================================
# FINISH POSITION
# ============================================================
#
# After the twelfth corner the car is back in its starting
# straight. We estimate how far down that straight the original
# starting point was from timings collected during the run.
#
# This value is used only if we could not learn enough clean
# straight sections.
# ============================================================

FINISH_FORWARD_FALLBACK_MS = 350

FINISH_FORWARD_MAX_MS = 1500
