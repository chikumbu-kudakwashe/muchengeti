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
# K210 COLOUR INDEXES
# ============================================================
#
# These indexes depend on the colour table stored inside the
# K210 firmware.
#
# Our current firmware setup uses:
#
#   1 = red
#   2 = green
#   3 = orange
#   4 = blue
#
# Verify 3 and 4 on the real camera before the competition.
# ============================================================

RED_INDEX = 1
GREEN_INDEX = 2

ORANGE_INDEX = 3
BLUE_INDEX = 4


# ============================================================
# STARTUP BLUE / ORANGE FILTERING
# ============================================================
#
# These values are deliberately permissive.
#
# We do not want to reject the line just because the lighting
# has made it darker or lighter than expected.
#
# IMPORTANT:
# These settings control blob acceptance. They do not change the
# actual LAB/HSV colour range stored inside the K210 firmware.
# ============================================================

START_COLOR_PIXELS_THRESHOLD = 40
START_COLOR_AREA_THRESHOLD = 40

START_COLOR_MIN_WIDTH = 4
START_COLOR_MIN_HEIGHT = 3
START_COLOR_MIN_AREA = 20

# The winning colour should be seen several times.
START_COLOR_MIN_VOTES = 2

# A colour should preferably lead the other by this many votes.
START_COLOR_VOTE_MARGIN = 2


# ============================================================
# TRAFFIC SIGN FILTERING
# ============================================================

TRAFFIC_PIXELS_THRESHOLD = 60
TRAFFIC_AREA_THRESHOLD = 60

TRAFFIC_MIN_WIDTH = 5
TRAFFIC_MIN_HEIGHT = 5
TRAFFIC_MIN_AREA = 40

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
TRAFFIC_SHIFT_SPEED = 150
TRAFFIC_PASS_SPEED = 170
TRAFFIC_RECENTER_SPEED = 150

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

# Begin the sideways avoidance once the pillar is this close.
TRAFFIC_PASS_TRIGGER_CM = 40

# ------------------------------------------------------------
# SIDESTEP SIZING
# ------------------------------------------------------------
#
# Pillars on this mat are not all the same distance into the lane
# - some sit close to the outer wall, others sit further toward
# the center obstacle. A single fixed shift is either too much or
# too little depending on where the pillar actually is, so the
# shift duration is scaled by how far off-center the pillar's
# camera blob (getCX) is at the moment we commit to passing it.
#
# CALIBRATE ON THE REAL CAMERA: TRAFFIC_CAMERA_CENTER_X should be
# the getCX reading for a pillar dead-center in frame, and
# TRAFFIC_CX_FULL_OFFSET_PX the offset (in the same units) at
# which the pillar is already at the edge of the lane.

TRAFFIC_CAMERA_CENTER_X = 160

TRAFFIC_CX_FULL_OFFSET_PX = 80

TRAFFIC_SHIFT_MS_MIN = 250
TRAFFIC_SHIFT_MS_MAX = 550

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

# After undoing the sideways shift, use the camera's line-following
# error to confirm the car is actually back at track center instead
# of trusting the timed strafe alone (motor response is never
# perfectly symmetric, so blind timing drifts over a run).
#
# The reading must stay centered for this long before the pillar
# manoeuvre is considered complete.
RECENTER_CONFIRM_MS = 120

# Do not let camera-based recentering run forever if the track
# camera cannot get a usable reading (e.g. still mid-shift).
RECENTER_CAMERA_TIMEOUT_MS = 700

# Camera scan interval while travelling on the straight.
TRAFFIC_SCAN_INTERVAL_MS = 250


# ============================================================
# ULTRASONIC
# ============================================================

ULTRASONIC_INTERVAL_MS = 80


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