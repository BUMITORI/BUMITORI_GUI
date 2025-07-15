import sys
import json
import serial
import requests
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt, QThread, pyqtSignal

# 학생 정보 불러오기
def load_students():
    try:
        with open("students.json", "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as e:
        print("students.json 파일을 열 수 없습니다.", e)
        return {}

# UART 초기화 함수
def init_uart():
    try:
        uart = serial.Serial("/dev/ttyAMA0", 9600, timeout=1)
        return uart
    except serial.SerialException as e:
        print(f"UART 포트를 열 수 없습니다: {e}")
        return None

class UartThread(QThread):
    message_signal = pyqtSignal(str)

    def __init__(self, uart, students):
        super().__init__()
        self.uart = uart
        self.students = students

    def run(self):
        while True:
            if self.uart.in_waiting > 0:
                rfid = self.uart.readline().decode("utf-8").strip()
                self.handle_rfid(rfid)

    def handle_rfid(self, rfid):
        try:
            # 16진수 문자열을 10진수 정수로 변환
            rfid_decimal = int(rfid, 16)

            # 서버에 10진수 rfid 전송
            response = requests.post(
                "https://bumitori.duckdns.org/checkin",
                data={"rfid": str(rfid_decimal)}
            )
            print(f"[서버 응답] {response.status_code}: {response.text}")
        except ValueError:
            print(f"[변환 오류] RFID가 유효한 16진수 아님: {rfid}")
        except requests.RequestException as e:
            print(f"[요청 실패] RFID 전송 중 오류 발생: {e}")

        if rfid in self.students:
            name = self.students[rfid]
            message = f"{name} 출석이 완료되었습니다."
        else:
            message = "카드를 찍어주세요"

        self.message_signal.emit(message)

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("출석 관리 시스템")
        self.setGeometry(100, 100, 300, 150)

        self.label = QLabel("카드를 찍어주세요", self)
        self.label.setAlignment(Qt.AlignCenter)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.label)
        self.setLayout(self.layout)

        # 학생 정보 로드
        self.students = load_students()

        # UART 초기화
        self.uart = init_uart()
        if self.uart is None:
            sys.exit(1)

        # UART 데이터 읽기 스레드 시작
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
