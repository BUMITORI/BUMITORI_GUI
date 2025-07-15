import sys
import json
import serial
import requests
import time
import re
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont

# 학생 정보 불러오기
def load_students():
    try:
        with open("students.json", "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as e:
        print("에러: students.json 불러오기 실패:", e)
        return {}

# UART 초기화
def init_uart():
    try:
        uart = serial.Serial("/dev/ttyAMA0", 9600, timeout=1)
        return uart
    except serial.SerialException as e:
        print(f"에러: UART 포트 열기 실패: {e}")
        return None

class UartThread(QThread):
    message_signal = pyqtSignal(str)

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

                # 8자리 16진수 형식이 아닌 값은 무시
                if not re.fullmatch(r"[0-9a-fA-F]{8}", ascii_str):
                    continue

                rfid_hex = ascii_str.lower()
                current_time = time.time()

                # 3초 이내 동일 태그 무시
                if (current_time - self.last_time) < 3 and rfid_hex == self.last_rfid:
                    continue

                self.last_rfid = rfid_hex
                self.last_time = current_time
                self.handle_rfid(rfid_hex)

    def handle_rfid(self, rfid_hex):
        print(f"[RFID 수신] {rfid_hex}")

        try:
            rfid_decimal = int(rfid_hex, 16)
        except ValueError:
            print(f"[무시됨] 유효하지 않은 RFID: {rfid_hex}")
            return

        message = "카드를 인식 중입니다..."

        try:
            response = requests.post(
                "https://bumitori.duckdns.org/checkin",
                data={"rfid": str(rfid_decimal)}
            )
            print(f"[서버 응답] {response.status_code}: {response.text}")

            if response.status_code == 200:
                message = "입사가 완료되었습니다"
            else:
                message = "입사 실패: 서버 응답 오류"
        except requests.RequestException as e:
            print(f"[요청 실패] 서버 연결 오류: {e}")
            message = "서버 연결 실패"

        self.message_signal.emit(message)

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("입사 체크 시스템")
        self.setGeometry(100, 100, 400, 200)

        self.label = QLabel("카드를 찍어주세요", self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setFont(QFont("Arial", 14))

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

        self.reset_timer = QTimer()
        self.reset_timer.setSingleShot(True)
        self.reset_timer.timeout.connect(self.reset_message)

    def update_message(self, message):
        self.label.setText(message)
        if message == "입사가 완료되었습니다":
            self.reset_timer.start(5000)
        else:
            self.reset_timer.start(2000)

    def reset_message(self):
        self.label.setText("카드를 찍어주세요")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
