from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout,
    QTableWidget, QTableWidgetItem, QTextEdit
)
from PyQt6.QtGui import QPainter, QColor, QFont
from PyQt6.QtCore import Qt


# =========================
# REGISTER TABLE
# =========================
class RegisterTable(QTableWidget):
    def __init__(self):
        super().__init__(16, 4)  # 16 rânduri, 4 coloane (2 registre pe rând)

        self.setHorizontalHeaderLabels(["Registru", "Valoare (hex)", "Registru", "Valoare (hex)"])
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        # font monospaced pentru valori
        font = QFont("Courier")
        
        self.register_names = [f"x{i}" for i in range(32)]

        for row in range(16):
            # Registru stânga
            name_left = self.register_names[row]
            self.setItem(row, 0, QTableWidgetItem(name_left))
            item_val_left = QTableWidgetItem("0x0000000000000000")
            item_val_left.setFont(font)
            self.setItem(row, 1, item_val_left)

            # Registru dreapta
            name_right = self.register_names[row + 16]
            self.setItem(row, 2, QTableWidgetItem(name_right))
            item_val_right = QTableWidgetItem("0x0000000000000000")
            item_val_right.setFont(font)
            self.setItem(row, 3, item_val_right)

        # Lățimi coloane
        self.setColumnWidth(0, 70)   # nume registru stânga
        self.setColumnWidth(1, 180)  # valoare hex stânga
        self.setColumnWidth(2, 70)   # nume registru dreapta
        self.setColumnWidth(3, 180)  # valoare hex dreapta

    def update_registers(self, registers):
        """registers = dict[str, int]"""
        for row in range(16):
            # Registru stânga
            name_left = self.register_names[row]
            value_left = registers.get(name_left, 0)
            self.item(row, 1).setText(f"0x{value_left & 0xFFFFFFFFFFFFFFFF:016X}")

            # Registru dreapta
            name_right = self.register_names[row + 16]
            value_right = registers.get(name_right, 0)
            self.item(row, 3).setText(f"0x{value_right & 0xFFFFFFFFFFFFFFFF:016X}")



# =========================
# LED
# =========================
class LedCircle(QWidget):
    def __init__(self, diameter=25):
        super().__init__()
        self.on = False
        self.setFixedSize(diameter, diameter)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        size = min(self.width(), self.height())
        color = QColor("green") if self.on else QColor("red")

        painter.setBrush(color)
        painter.setPen(QColor("black"))
        painter.drawEllipse(0, 0, size, size)

    def set_state(self, state: bool):
        self.on = state
        self.update()


# =========================
# MAIN PANEL
# =========================
class LedPanel(QWidget):
    def __init__(self, processor):
        super().__init__()
        self.processor = processor

        self.setWindowTitle("Simulator RISC-V")
        self.resize(1050, 525)

        main_layout = QHBoxLayout(self)

        # ================= LEFT =================
        left_layout = QVBoxLayout()

        led_layout = QHBoxLayout()
        self.leds = []
        for _ in range(16):
            led = LedCircle()
            self.leds.append(led)
            led_layout.addWidget(led)

        left_layout.addLayout(led_layout)

        self.textbox = QTextEdit()
        self.textbox.setPlaceholderText("Ieșire / debug")
        self.textbox.setReadOnly(True)
        left_layout.addWidget(self.textbox)

        # ================= RIGHT =================
        self.reg_table = RegisterTable()

        main_layout.addLayout(left_layout, 1)
        main_layout.addWidget(self.reg_table, 1)

    def update_leds_from_result(self, result):
        for i in range(16):
            bit = (result >> i) & 1
            self.leds[15 - i].set_state(bit == 1)
    def append_text(self, text):
        self.textbox.append(text)
    def reset_text(self):
        self.textbox.setPlainText("")

