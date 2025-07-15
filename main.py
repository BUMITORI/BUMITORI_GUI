import sys
import json
import serial
import requests
import time
import re
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPalette, QColor


# 학생 정보 로드
def load_students():
  try:
    with open("students.json", "r", encoding="utf-8") as file:
      return json.load(file)
  except Exception as e:
    print("오류: students.json 파일을 불러올 수 없습니다:", e)
    return {}


# UART 포트 초기화
def init_uart():
  try:
    uart = serial.Serial("/dev/ttyAMA0", 9600, timeout=1)
    return uart
  except serial.SerialException as e:
    print(f"오류: UART 포트를 열 수 없습니다: {e}")
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
    print(f"[RFID 수신됨] {rfid_hex}")
    try:
      rfid_decimal = int(rfid_hex, 16)
    except ValueError:
      print(f"[무시됨] 잘못된 RFID 형식: {rfid_hex}")
      return

    try:
      response = requests.post(
        "https://bumitori.duckdns.org/checkin",
        data={"rfid": str(rfid_decimal)}
      )
      print(f"[서버 응답] {response.status_code}: {response.text}")

      if response.status_code == 200:
        self.message_signal.emit("✅ 입사 처리가 완료되었습니다", True)
      else:
        self.message_signal.emit("❌ 입사 처리에 실패했습니다", False)

    except requests.RequestException as e:
      print(f"[요청 실패] 서버에 RFID 전송 중 오류 발생: {e}")
      self.message_signal.emit("❌ 서버 연결 실패", False)


class MainWindow(QWidget):
  def __init__(self):
    super().__init__()
    self.setWindowTitle("입사 관리 시스템")
    self.setGeometry(100, 100, 400, 200)

    palette = self.palette()
    palette.setColor(QPalette.Window, QColor("#f0f0f0"))
    self.setPalette(palette)

    font = QFont("Arial", 16, QFont.Bold)
    self.label = QLabel("카드를 태그해주세요", self)
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
    self.label.setText("카드를 태그해주세요")


if __name__ == "__main__":
  app = QApplication(sys.argv)
  window = MainWindow()
  window.show()
  sys.exit(app.exec_())
