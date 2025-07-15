import sys
import json
import serial
import requests
import time
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt, QThread, pyqtSignal

# Load student data from JSON
def load_students():
    try:
        with open("students.json", "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as e:
        print("Error: Failed to load students.json:", e)
        return {}

# Initialize UART
def init_uart():
    try:
        uart = serial.Serial("/dev/ttyAMA0", 9600, timeout=1)
        return uart
    except serial.SerialException as e:
        print(f"Error: Failed to open UART port: {e}")
        return None

class UartThread(QThread):
    message_signal = pyqtSignal(str)

    def __init__(self, uart, students):
        super().__init__()
        self.uart = uart
        self.students = students
        self.last_rfid = None
        self.last_time = 0  # Time of last valid scan

    def run(self):
        while True:
            if self.uart.in_waiting > 0:
                data = self.uart.readline()
                rfid_hex = data.hex().strip().lower()

                # Ignore short or invalid input
                if len(rfid_hex) < 8:
                    continue

                current_time = time.time()

                # Ignore if scanned within 3 seconds
                if (current_time - self.last_time) < 3:
                    continue

                self.last_rfid = rfid_hex
                self.last_time = current_time
                self.handle_rfid(rfid_hex)

    def handle_rfid(self, rfid_hex):
        print(f"[RFID received] {rfid_hex}")

        try:
            rfid_decimal = int(rfid_hex, 16)
        except ValueError:
            print(f"[Ignored] Invalid hex string: {rfid_hex}")
            return

        try:
            response = requests.post(
                "https://bumitori.duckdns.org/checkin",
                data={"rfid": str(rfid_decimal)}
            )
            print(f"[Server response] {response.status_code}: {response.text}")
        except requests.RequestException as e:
            print(f"[Request failed] Error while sending RFID to server: {e}")

        if rfid_hex in self.students:
            name = self.students[rfid_hex]
            message = f"Check-in completed: {name}"
        else:
            message = "Please tap your card"

        self.message_signal.emit(message)

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Check-in Management System")
        self.setGeometry(100, 100, 300, 150)

        self.label = QLabel("Please tap your card", self)
        self.label.setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)

        self.students = load_students()
        self.uart = init_uart()
        if self.uart is None:
            sys.exit(1)

        self.uart_thread = UartThread(self.uart, self.students)
        self.uart_thread.message_signal.connect(self.update_message)
        self.uart_thread.start()

    def update_message(self, message):
        self.label.setText(message)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
