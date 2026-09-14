from machine import UART, Pin, PWM
import time


class ACB_Canmv:
    def __init__(self):
        self.uart = None

        self.set_mode = 0
        self.red_value = 0
        self.green_value = 0
        self.blue_value = 0
        self.color_index = 0

        self.SDA = 21
        self.SCL = 22

        self.UartBuff = bytearray(128)

        # parsed outputs
        self.getX = 0
        self.getY = 0
        self.getW = 0
        self.getH = 0
        self.getCX = 0
        self.getCY = 0
        self.Visual_data = 0
        self.getTag = ""

    # -------- low-level helpers --------
    def init(self, rx_pin, tx_pin, baudrate=115200, uart_id=1, timeout_ms=50):

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
        time.sleep_ms(50)
        self._flush()
              
    def _flush(self):
        if not self.uart:
            return
        while self.uart.any(): 
            self.uart.read()

    def sendCommand(self, cmd: str):

        if not self.uart:
            return
        self.uart.write(cmd.encode("utf-8"))
        self.uart.write(b"\r\n")

    def _write_packet(self, data: bytes):
        if not self.uart:
            return
        self.uart.write(data)
        time.sleep_ms(100)

    def _read_frame(self, max_wait_ms=200):

        if not self.uart:
            return None

        t0 = time.ticks_ms()
        while self.uart.any() < 1:
            if time.ticks_diff(time.ticks_ms(), t0) > max_wait_ms:
                return None

        b = self.uart.read(1)
        if not b:
            return None
        data_len = b[0]

        t0 = time.ticks_ms()
        while self.uart.any() < data_len:
            if time.ticks_diff(time.ticks_ms(), t0) > max_wait_ms:
                return None

        payload = self.uart.read(data_len)
        return payload

    @staticmethod
    def _u16(msb, lsb):
        return (msb << 8) | lsb

    # -------- high-level functions --------
    def Default_menu(self):
        if self.set_mode != 0:
            self.set_mode = 0
            self._write_packet(bytes([self.set_mode, 13, 10]))  # \r\n

    def RGB_set(self, red, green, blue):
        if (self.red_value != red) or (self.green_value != green) or (self.blue_value != blue):
            pkt = bytes([self.set_mode, 255, red, green, blue, 13, 10])
            self._write_packet(pkt)

        self.red_value = red
        self.green_value = green
        self.blue_value = blue

    def color_recognize(self, index, pixels_threshold, area_threshold):
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
        if not payload:
            return False

        if len(payload) < 9:
            return False

        self.getX = self._u16(payload[0], payload[1])
        self.getY = payload[2]
        self.getW = self._u16(payload[3], payload[4])
        self.getH = payload[5]
        self.getCX = self._u16(payload[6], payload[7])
        self.getCY = payload[8]
        self.getTag = payload[9:].decode() if len(payload) > 9 else ""
        return True

    def qrcode_recognize(self):
        if self.set_mode != 2:
            self.set_mode = 2
            self._write_packet(bytes([self.set_mode, 13, 10]))

        payload = self._read_frame()
        if not payload:
            return False

        if len(payload) < 6:
            return False
        self.getX = self._u16(payload[0], payload[1])
        self.getY = payload[2]
        self.getW = self._u16(payload[3], payload[4])
        self.getH = payload[5]
        self.getTag = payload[6:].decode() if len(payload) > 6 else ""
        return True

    def barcode_recognize(self):
        if self.set_mode != 3:
            self.set_mode = 3
            self._write_packet(bytes([self.set_mode, 13, 10]))

        payload = self._read_frame()
        if not payload:
            return False
        if len(payload) < 6:
            return False
        self.getX = self._u16(payload[0], payload[1])
        self.getY = payload[2]
        self.getW = self._u16(payload[3], payload[4])
        self.getH = payload[5]
        self.getTag = payload[6:].decode() if len(payload) > 6 else ""
        return True

    def face_recognize(self):
        if self.set_mode != 4:
            self.set_mode = 4
            self._write_packet(bytes([self.set_mode, 13, 10]))

        payload = self._read_frame()
        if not payload:
            return False
        if len(payload) < 7:
            return False
        self.getX = self._u16(payload[0], payload[1])
        self.getY = payload[2]
        self.getW = self._u16(payload[3], payload[4])
        self.getH = payload[5]
        self.getCX = self._u16(payload[6], payload[7])
        self.getCY = payload[8]
        self.getTag = "ID{}".format(payload[9])
        return True

    def image_recognize(self):
        if self.set_mode != 5:
            self.set_mode = 5
            self._write_packet(bytes([self.set_mode, 13, 10]))

        payload = self._read_frame()
        if not payload:
            return False

        if len(payload) < 9:
            return False

        self.getX = self._u16(payload[0], payload[1])
        self.getY = payload[2]
        self.getW = self._u16(payload[3], payload[4])
        self.getH = payload[5]
        self.getCX = self._u16(payload[6], payload[7])
        self.getCY = payload[8]
        self.getTag = payload[9:].decode() if len(payload) > 9 else ""
        return True

    def number_recognize(self):
        if self.set_mode != 6:
            self.set_mode = 6
            self._write_packet(bytes([self.set_mode, 13, 10]))

        payload = self._read_frame()
        if not payload:
            return False
        self.getTag = str(payload[0]) if len(payload) > 0 else ""
        return True

    def Traffic_recognize(self, mode):
        if self.set_mode != 7:
            self.set_mode = 7
            pkt = bytes([self.set_mode, mode, 13, 10])
            self._write_packet(pkt)

        payload = self._read_frame()
        if not payload:
            return False
        if len(payload) < 9:
            return False

        self.getX = self._u16(payload[0], payload[1])
        self.getY = payload[2]
        self.getW = self._u16(payload[3], payload[4])
        self.getH = payload[5]
        self.getCX = self._u16(payload[6], payload[7])
        self.getCY = payload[8]
        self.getTag = payload[9:].decode() if len(payload) > 9 else ""
        return True

    def visual_patrol(self):
        if self.set_mode != 8:
            self.set_mode = 8
            self._write_packet(bytes([self.set_mode, 13, 10]))

        payload = self._read_frame()
        if not payload:
            return False
        if len(payload) < 1:
            return False
        self.Visual_data = payload[0] - 60
        return True

    def machine_learning(self):
        if self.set_mode != 9:
            self.set_mode = 9
            self._write_packet(bytes([self.set_mode, 13, 10]))

        payload = self._read_frame()
        if not payload:
            return False
        if len(payload) < 1:
            return False
        self.getTag = "Class{}".format(payload[0])
        return True
