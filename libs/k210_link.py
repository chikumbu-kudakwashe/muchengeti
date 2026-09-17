from machine import UART, Pin
import time


class K210Link:
    """
    ESP32-side driver for the new Muchengeti K210 vision runtime
    (see K210 main.py / README_K210.txt). Replaces libs.ACB_Canmv,
    which spoke the original ACEBOTT binary packet protocol - this
    firmware instead streams plain text lines and only reports
    colour blobs (no line-following/visual-patrol support).

    Protocol:
        ESP32 -> K210 (newline-terminated ASCII):
            MODE START      -> only BLUE/ORANGE are reported
            MODE TRAFFIC    -> only RED/GREEN are reported
            MODE ALL        -> all four
            PING            -> replies PONG

        K210 -> ESP32, one line per camera frame:
            C,<COLOR>,cx,cy,w,h,pixels
            C,NONE,0,0,0,0,0
    """

    MODE_START = "START"
    MODE_TRAFFIC = "TRAFFIC"
    MODE_ALL = "ALL"

    def __init__(
        self,
        rx_pin: int,
        tx_pin: int,
        baudrate: int = 115200,
        uart_id: int = 1,
        timeout_ms: int = 50
    ) -> None:
        """
        Open the UART link to the K210 and set the initial state.

        Args:
            rx_pin: ESP32 pin wired to the K210's TX line.
            tx_pin: ESP32 pin wired to the K210's RX line.
            baudrate: Must match the K210 runtime's UART_BAUD.
            uart_id: ESP32 UART peripheral to use.
            timeout_ms: Read timeout passed to the UART driver.

        Returns:
            None.
        """

        self.uart = UART(
            uart_id,
            baudrate=baudrate,
            bits=8,
            parity=None,
            stop=1,
            rx=Pin(rx_pin),
            tx=Pin(tx_pin),
            timeout=timeout_ms
        )

        self.mode = None

        self.name = None
        self.cx = 0
        self.cy = 0
        self.w = 0
        self.h = 0
        self.pixels = 0

        time.sleep_ms(50)

        self._flush()


    def _flush(self) -> None:
        """
        Discard any bytes already sitting in the UART buffer.
        """

        while self.uart.any():
            self.uart.read()


    def set_mode(self, mode: str) -> None:
        """
        Tell the K210 which colours to report.

        A no-op when already in the requested mode, so callers can
        call this on every detect() without spamming the UART link.

        Args:
            mode: One of MODE_START, MODE_TRAFFIC, MODE_ALL.

        Returns:
            None.
        """

        if self.mode == mode:
            return

        self.mode = mode

        self.uart.write("MODE %s\r\n" % mode)


    def _read_line(self):
        """
        Read one available line from the UART, if any.

        Returns:
            Decoded, stripped line, or None.
        """

        if not self.uart.any():
            return None

        try:
            raw = self.uart.readline()
        except Exception:
            return None

        if not raw:
            return None

        try:
            return raw.decode().strip()
        except Exception:
            return None


    def poll(self) -> bool:
        """
        Read the newest available detection and store it.

        Multiple lines may have queued up since the last poll - only
        the most recent is kept so a busy buffer never leaves us
        reacting to a stale detection.

        Returns:
            True if a colour (not NONE) is currently reported.
        """

        line = self._read_line()

        while True:

            newer = self._read_line()

            if newer is None:
                break

            line = newer

        if line is None:

            return self.name is not None

        if not line.startswith("C,"):

            return self.name is not None

        parts = line.split(",")

        if len(parts) != 7:

            return self.name is not None

        name = parts[1]

        if name == "NONE":

            self.name = None
            self.cx = 0
            self.cy = 0
            self.w = 0
            self.h = 0
            self.pixels = 0

            return False

        try:

            self.name = name.lower()
            self.cx = int(parts[2])
            self.cy = int(parts[3])
            self.w = int(parts[4])
            self.h = int(parts[5])
            self.pixels = int(parts[6])

        except ValueError:

            self.name = None

            return False

        return True
