import sys
import json
import serial
import requests
import time
import re
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPalette, QColor


def load_students():
  try:
    with open("students.json", "r", encoding="utf-8") as file:
      return json.load(file)
  except Exception as e:
    print("Error: Failed to load students.json:", e)
    return {}


def init_uart():
  try:
    uart = serial.Serial("/dev/ttyAMA0", 9600, timeout=1)
    return uart
  except serial.SerialException as e:
    print(f"Error: Failed to open UART port: {e}")
    return None


class UartThread(QThread):
  message_signal = pyqtSignal(str, bool)  # 메시지, 성공 여부(True/False)

  def __init__(self, uart, students):
    super().__init__()
    self.uart = uart
    self.students = students
    self.last_rfid = None
    self.last_time = 0

  def run(self):
    while True:
      if self.uart.in_waiting > 0:
        raw_data = self.uart.readline()
        try:
          ascii_str = raw_data.decode("utf-8").strip()
        except UnicodeDecodeError:
          continue
        hex_str = re.sub(r'[^0-9a-fA-F]', '', ascii_str)
        if len(hex_str) < 8:
          continue
        rfid_hex = hex_str.lower()
        current_time = time.time()
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

      if response.status_code == 200:
        self.message_signal.emit("✅ Check-in successful", True)
      else:
        self.message_signal.emit("❌ Check-in failed", False)

    except requests.RequestException as e:
      print(f"[Request failed] Error while sending RFID to server: {e}")
      self.message_signal.emit("❌ Server error", False)


class MainWindow(QWidget):
  def __init__(self):
    super().__init__()
    self.setWindowTitle("Check-in Management System")
    self.setGeometry(100, 100, 400, 200)

    # 배경색
    palette = self.palette()
    palette.setColor(QPalette.Window, QColor("#f0f0f0"))
    self.setPalette(palette)

    # 라벨 스타일
    font = QFont("Arial", 16, QFont.Bold)
    self.label = QLabel("Please tap your card", self)
    self.label.setFont(font)
    self.label.setAlignment(Qt.AlignCenter)
    self.label.setStyleSheet("color: #333333; padding: 20px;")

    layout = QVBoxLayout()
    layout.addWidget(self.label)
    self.setLayout(layout)

    self.reset_timer = QTimer()
    self.reset_timer.setSingleShot(True)
    self.reset_timer.timeout.connect(self.reset_message)

    self.students = load_students()
    self.uart = init_uart()
    if self.uart is None:
      sys.exit(1)

    self.uart_thread = UartThread(self.uart, self.students)
    self.uart_thread.message_signal.connect(self.update_message)
    self.uart_thread.start()

  def update_message(self, message, is_success):
    self.label.setText(message)
    if is_success:
      self.reset_timer.start(5000)  # 5초 후 초기화

  def reset_message(self):
    self.label.setText("Please tap your card")


if __name__ == "__main__":
  app = QApplication(sys.argv)
  window = MainWindow()
  window.show()
  sys.exit(app.exec_())
