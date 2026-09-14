from machine import UART, Pin
import time

class ACB_Canmv:
    def __init__(self):
        self.uart = None
        self.set_mode = -1  # Forces configuration change on the first loop iteration
        self.red_value = 0
        self.green_value = 0
        self.blue_value = 0
        self.color_index = 0

        # Parsed output properties
        self.getX = 0
        self.getY = 0
        self.getW = 0
        self.getH = 0
        self.getCX = 0
        self.getCY = 0
        self.Visual_data = 0
        self.getTag = ""

    def init(self, rx_pin=16, tx_pin=17, baudrate=115200, uart_id=1):
        # Timeout=0 ensures serial checking is completely non-blocking
        self.uart = UART(
            uart_id,
            baudrate=baudrate,
            bits=8,
            parity=None,
            stop=1,
            rx=Pin(rx_pin),
            tx=Pin(tx_pin),
            timeout=0 
        )
        time.sleep_ms(50)
        self._flush()

    def _flush(self):
        if not self.uart:
            return
        while self.uart.any(): 
            self.uart.read()

    def _write_packet(self, data: bytes):
        if not self.uart:
            return
        self.uart.write(data)

    def _read_frame(self):
        """Non-blocking frame reader that prevents the video feed from freezing."""
        if not self.uart or self.uart.any() < 1:
            return None

        # Read the payload length indicator byte
        len_byte = self.uart.read(1)
        if not len_byte:
            return None
        data_len = len_byte[0]  # Extracts byte integer

        # Quick collection window for incoming stream
        t0 = time.ticks_ms()
        while self.uart.any() < data_len:
            if time.ticks_diff(time.ticks_ms(), t0) > 10: 
                return None

        return self.uart.read(data_len)

    @staticmethod
    def _u16(msb, lsb):
        return (msb << 8) | lsb

    def color_recognize(self, index, pixels_threshold, area_threshold):
        # Instruct the camera to switch to color recognition mode if not already running
        if (self.set_mode != 1) or (index != self.color_index):
            self.set_mode = 1
            self.color_index = index
            pkt = bytes([
                self.set_mode,
                self.color_index,
                (area_threshold >> 8) & 0xFF, area_threshold & 0xFF,
                (pixels_threshold >> 8) & 0xFF, pixels_threshold & 0xFF,
                13, 10
            ])
            self._write_packet(pkt)

        payload = self._read_frame()
        if not payload or len(payload) < 9:
            return False

        # Correctly indexes bytes to recreate the coordinates
        self.getX = self._u16(payload[0], payload[1])
        self.getY = payload[2]
        self.getW = self._u16(payload[3], payload[4])
        self.getH = payload[5]
        self.getCX = self._u16(payload[6], payload[7])
        self.getCY = payload[8]
        self.getTag = payload[9:].decode(errors='ignore') if len(payload) > 9 else ""
        return True
