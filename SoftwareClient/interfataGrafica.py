from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout,
    QTableWidget, QTableWidgetItem, QTextEdit
)
from PyQt6.QtGui import QPainter, QColor, QFont
from PyQt6.QtCore import Qt

class RegisterTable(QTableWidget):
    def __init__(self):
        super().__init__(16, 4)  # 16 randuri, 4 coloane (2 registre pe rand)

        self.setHorizontalHeaderLabels(["Registru", "Valoare (hex)", "Registru", "Valoare (hex)"])
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        # font Courier pentru valori
        font = QFont("Courier")
        
        self.register_keys = [f"x{i}" for i in range(32)]
        
        self.register_display = [
            "x0 (zero)", "x1 (ra)", "x2 (sp)", "x3 (gp)", "x4 (tp)",
            "x5 (t0)", "x6 (t1)", "x7 (t2)",
            "x8 (s0/fp)", "x9 (s1)",
            "x10 (a0)", "x11 (a1)", "x12 (a2)", "x13 (a3)", "x14 (a4)", "x15 (a5)",
            "x16 (a6)", "x17 (a7)",
            "x18 (s2)", "x19 (s3)", "x20 (s4)", "x21 (s5)", "x22 (s6)", "x23 (s7)",
            "x24 (s8)", "x25 (s9)", "x26 (s10)", "x27 (s11)",
            "x28 (t3)", "x29 (t4)", "x30 (t5)", "x31 (t6)"
        ]

        for row in range(16):
            self.setItem(row, 0, QTableWidgetItem(self.register_display[row]))
            item_val_left = QTableWidgetItem("0x0000000000000000")
            item_val_left.setFont(font)
            self.setItem(row, 1, item_val_left)

            self.setItem(row, 2, QTableWidgetItem(self.register_display[row + 16]))
            item_val_right = QTableWidgetItem("0x0000000000000000")
            item_val_right.setFont(font)
            self.setItem(row, 3, item_val_right)

            # Latimi coloane
            self.setColumnWidth(0, 70)   # nume registru stanga
            self.setColumnWidth(1, 180)  # valoare hex stanga
            self.setColumnWidth(2, 70)   # nume registru dreapta
            self.setColumnWidth(3, 180)  # valoare hex dreapta

    def update_registers(self, registers):
        for row in range(16):
            key_left = self.register_keys[row]
            value_left = registers.get(key_left, 0)
            self.item(row, 0).setText(self.register_display[row])
            self.item(row, 1).setText(f"0x{value_left & 0xFFFFFFFFFFFFFFFF:016X}")

            key_right = self.register_keys[row + 16]
            value_right = registers.get(key_right, 0)
            self.item(row, 2).setText(self.register_display[row + 16])
            self.item(row, 3).setText(f"0x{value_right & 0xFFFFFFFFFFFFFFFF:016X}")

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

class LedPanel(QWidget):
    def __init__(self, processor):
        super().__init__()
        self.processor = processor

        self.setWindowTitle("Simulator RISC-V")
        self.resize(1050, 525)

        main_layout = QHBoxLayout(self)

        left_layout = QVBoxLayout()

        led_layout = QHBoxLayout()
        self.leds = []
        for _ in range(16):
            led = LedCircle()
            self.leds.append(led)
            led_layout.addWidget(led)

        left_layout.addLayout(led_layout)

        self.textbox = QTextEdit()
        self.textbox.setPlaceholderText("Iesire / debug")
        self.textbox.setReadOnly(True)
        left_layout.addWidget(self.textbox)

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

