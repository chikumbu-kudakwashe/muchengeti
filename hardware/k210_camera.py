"""
Simple UART reader for the custom Muchengeti K210 camera program.

Expected K210 messages:

    C,BLUE,cx,cy,w,h,pixels
    C,ORANGE,cx,cy,w,h,pixels
    C,RED,cx,cy,w,h,pixels
    C,GREEN,cx,cy,w,h,pixels
    C,NONE,0,0,0,0,0

This module is for the ESP32.
"""

from machine import UART
import time


class K210Camera:
    """
    Read colour detections sent by the K210 over UART.
    """

    def __init__(
        self,
        uart_id: int = 1,
        tx_pin: int = 21,
        rx_pin: int = 22,
        baudrate: int = 115200
    ) -> None:
        """
        Initialise the UART connection.

        Args:
            uart_id: ESP32 UART number.
            tx_pin: ESP32 TX pin.
            rx_pin: ESP32 RX pin.
            baudrate: UART baud rate.

        Returns:
            None.
        """

        self.uart = UART(
            uart_id,
            baudrate=baudrate,
            tx=tx_pin,
            rx=rx_pin,
            timeout=50,
            timeout_char=10
        )

        self.buffer = ""


    def _parse_line(
        self,
        line: str
    ):
        """
        Parse one K210 detection line.

        Args:
            line: Raw UART line.

        Returns:
            Detection dictionary or None.
        """

        line = line.strip()


        if not line:

            return None


        if line.startswith(
            "K210,MUCHENGETI,READY"
        ):

            return {
                "type": "ready"
            }


        if not line.startswith(
            "C,"
        ):

            return None


        parts = line.split(",")


        if len(parts) != 7:

            return None


        color = (
            parts[1]
            .strip()
            .lower()
        )


        try:

            cx = int(
                parts[2]
            )

            cy = int(
                parts[3]
            )

            width = int(
                parts[4]
            )

            height = int(
                parts[5]
            )

            pixels = int(
                parts[6]
            )

        except Exception:

            return None


        return {
            "type": "color",

            "color": color,

            "cx": cx,

            "cy": cy,

            "width": width,

            "height": height,

            "pixels": pixels
        }


    def get_detection(
        self
    ):
        """
        Read and parse the newest complete UART message.

        Returns:
            Detection dictionary or None.
        """

        if not self.uart.any():

            return None


        raw = self.uart.read()


        if raw is None:

            return None


        try:

            text = raw.decode()

        except Exception:

            return None


        self.buffer += text


        detection = None


        while "\n" in self.buffer:

            line, self.buffer = (
                self.buffer.split(
                    "\n",
                    1
                )
            )


            parsed = (
                self._parse_line(
                    line
                )
            )


            if parsed is not None:

                detection = parsed


        return detection


    def flush(
        self
    ) -> None:
        """
        Clear any waiting UART data.

        Returns:
            None.
        """

        while self.uart.any():

            self.uart.read()


        self.buffer = ""


