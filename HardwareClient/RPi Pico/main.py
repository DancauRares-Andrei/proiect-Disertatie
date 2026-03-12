import time
import machine

uart = machine.UART(0, baudrate=57600, tx=machine.Pin(0), rx=machine.Pin(1))

LED_PINS = [machine.Pin(i + 2, machine.Pin.OUT) for i in range(16)]

def set_pins_from_result(result):
    for i in range(16):
        LED_PINS[i].value(1 if (result & (1 << i)) else 0)

STEP_DELAY_MS = 500

def sign_extend(number, bits):
    mask = (1 << bits) - 1
    number = number & mask
    if number & (1 << (bits - 1)):
        return number | (~mask & 0xFFFFFFFFFFFFFFFF)
    return number

def limit64(n):
    return n & 0xFFFFFFFFFFFFFFFF

def limit16(n):
    return n & 0xFFFF

def uart_read_exact(n, timeout_ms=10000):
    buf = bytearray()
    deadline = time.ticks_add(time.ticks_ms(), timeout_ms)
    while len(buf) < n:
        if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
            return None
        chunk = uart.read(n - len(buf))
        if chunk:
            buf.extend(chunk)
    return bytes(buf)

def receive_program():
    print("[PICO] Aștept program de la ESP...")

    header = uart_read_exact(4, timeout_ms=30000)
    if header is None:
        print("[PICO] Timeout la header!")
        uart.write(b"ERR\n")
        return None

    length = (header[0] << 24) | (header[1] << 16) | (header[2] << 8) | header[3]
    print(f"[PICO] Lungime program: {length} bytes")

    if length == 0 or length > 65536:
        print("[PICO] Lungime invalida!")
        uart.write(b"ERR\n")
        return None

    prog = uart_read_exact(length, timeout_ms=length + 5000)
    if prog is None or len(prog) != length:
        print("[PICO] Eroare recepție program!")
        uart.write(b"ERR\n")
        return None

    uart.write(b"OK\n")
    print(f"[PICO] Program recepționat ({length} bytes).")
    return bytearray(prog)

class RISCVProcessor:

    DATA_MEM_SIZE = 100

    def __init__(self):
        self.pc          = 0
        self.Jump        = False
        self.jumpAddress = 0
        self.registers   = [0] * 32
        self.dataMemory  = [0] * self.DATA_MEM_SIZE
        self.memory      = bytearray()

    def load(self, program: bytearray):
        self.memory      = program
        self.pc          = 0
        self.Jump        = False
        self.jumpAddress = 0
        self.registers   = [0] * 32
        self.dataMemory  = [0] * self.DATA_MEM_SIZE
        print(f"[CPU] Program încărcat: {len(program)} bytes.")

    def _fetch(self):
        pc = self.pc
        return (self.memory[pc+3] << 24 | self.memory[pc+2] << 16 |
                self.memory[pc+1] <<  8 | self.memory[pc])

    def execute(self):
        instr  = self._fetch()
        opcode = instr & 0x7F
        funct3 = (instr >> 12) & 0x7
        funct7 = (instr >> 25) & 0x7F
        imm12  = (instr >> 20) & 0xFFF
        shamt  = (instr >> 20) & 0x1F
        rs1    = (instr >> 15) & 0x1F
        rs2    = (instr >> 20) & 0x1F
        rd     = (instr >>  7) & 0x1F
        result = 0
        self.Jump = False

        regs = self.registers

        if opcode == 0b0110011:          # ── Tip R ──
            if   funct3 == 0 and funct7 == 0x00: regs[rd] = limit64(regs[rs1] + regs[rs2])          # ADD
            elif funct3 == 0 and funct7 == 0x20: regs[rd] = limit64(regs[rs1] - regs[rs2])          # SUB
            elif funct3 == 1:                     regs[rd] = limit64(regs[rs1] << (regs[rs2] & 0x1F))# SLL
            elif funct3 == 2:                     regs[rd] = 1 if (regs[rs1] - regs[rs2]) >> 63 else 0 # SLT
            elif funct3 == 3:                     regs[rd] = 1 if regs[rs1] < regs[rs2] else 0      # SLTU
            elif funct3 == 4:                     regs[rd] = limit64(regs[rs1] ^ regs[rs2])         # XOR
            elif funct3 == 5 and funct7 == 0x00:  regs[rd] = limit64(regs[rs1] >> (regs[rs2] & 0x1F))# SRL
            elif funct3 == 5 and funct7 == 0x20:  regs[rd] = limit64(regs[rs1] >> (regs[rs2] & 0x1F))# SRA
            elif funct3 == 6:                     regs[rd] = limit64(regs[rs1] | regs[rs2])         # OR
            elif funct3 == 7:                     regs[rd] = limit64(regs[rs1] & regs[rs2])         # AND
            result = limit16(regs[rd])

        elif opcode == 0b0010011:        # ── Tip I (ALU) ──
            imm = sign_extend(imm12, 12)
            if   funct3 == 0: regs[rd] = limit64(regs[rs1] + imm)                                   # ADDI
            elif funct3 == 1: regs[rd] = limit64(regs[rs1] << shamt)                                # SLLI
            elif funct3 == 2: regs[rd] = limit64(regs[rs1] - imm) >> 63                             # SLTI
            elif funct3 == 3: regs[rd] = 1 if regs[rs1] < imm else 0                                # SLTIU
            elif funct3 == 4: regs[rd] = limit64(regs[rs1] ^ imm)                                   # XORI
            elif funct3 == 5 and funct7 == 0x00: regs[rd] = limit64(regs[rs1] >> shamt)             # SRLI
            elif funct3 == 5 and funct7 == 0x20: regs[rd] = limit64(regs[rs1] >> shamt)             # SRAI
            elif funct3 == 6: regs[rd] = limit64(regs[rs1] | imm)                                   # ORI
            elif funct3 == 7: regs[rd] = limit64(regs[rs1] & imm)                                   # ANDI
            result = limit16(regs[rd])

        elif opcode == 0b0000011:        # ── Load ──
            addr = limit64(regs[rs1] + sign_extend(imm12, 12)) % self.DATA_MEM_SIZE
            if   funct3 == 0: regs[rd] = sign_extend(self.dataMemory[addr] & 0xFF,        8)        # LB
            elif funct3 == 1: regs[rd] = sign_extend(self.dataMemory[addr] & 0xFFFF,     16)        # LH
            elif funct3 == 2: regs[rd] = sign_extend(self.dataMemory[addr] & 0xFFFFFFFF, 32)        # LW
            elif funct3 == 3: regs[rd] = self.dataMemory[addr]                                      # LD
            elif funct3 == 4: regs[rd] = self.dataMemory[addr] & 0xFF                               # LBU
            elif funct3 == 5: regs[rd] = self.dataMemory[addr] & 0xFFFF                             # LHU
            elif funct3 == 6: regs[rd] = self.dataMemory[addr] & 0xFFFFFFFF                         # LWU
            result = limit16(regs[rd])

        elif opcode == 0b0100011:        # ── Store ──
            # De verificat: imm pentru Store = imm[11:5] || imm[4:0]
            imm_s = ((instr >> 25) << 5) | ((instr >> 7) & 0x1F)
            addr  = limit64(regs[rs1] + sign_extend(imm_s, 12)) % self.DATA_MEM_SIZE
            if   funct3 == 0: self.dataMemory[addr] = regs[rs2] & 0xFF                              # SB
            elif funct3 == 1: self.dataMemory[addr] = regs[rs2] & 0xFFFF                            # SH
            elif funct3 == 2: self.dataMemory[addr] = regs[rs2] & 0xFFFFFFFF                        # SW
            elif funct3 == 3: self.dataMemory[addr] = regs[rs2]                                     # SD
            result = limit16(self.dataMemory[addr])

        elif opcode == 0b0110111:        # ── LUI ──
            regs[rd] = limit64(sign_extend(instr >> 12, 20) << 12)
            result = limit16(regs[rd])

        elif opcode == 0b0010111:        # ── AUIPC ──
            regs[rd] = limit64(self.pc + (sign_extend(instr >> 12, 20) << 12))
            result = limit16(regs[rd])

        elif opcode == 0b1101111:        # ── JAL ──
            # imm[20|10:1|11|19:12] × 2
            jal_imm = (((instr >> 31) & 1) << 20 | ((instr >> 12) & 0xFF) << 12 |
                       ((instr >> 20) & 1) << 11  | ((instr >> 21) & 0x3FF) << 1)
            regs[rd]          = limit64(self.pc + 4)
            self.jumpAddress  = limit64(self.pc + sign_extend(jal_imm, 21))
            self.Jump         = True
            result            = limit16(self.jumpAddress)

        elif opcode == 0b1100111:        # ── JALR ──
            target            = limit64(regs[rs1] + sign_extend(imm12, 12)) & ~1
            regs[rd]          = limit64(self.pc + 4)
            self.jumpAddress  = target
            self.Jump         = True
            result            = limit16(self.jumpAddress)

        elif opcode == 0b1100011:        # ── Branch ──
            b_imm = (((instr >> 31) & 1) << 12 | ((instr >> 7) & 1) << 11 |
                     ((instr >> 25) & 0x3F) << 5 | ((instr >> 8) & 0xF) << 1)
            self.jumpAddress = limit64(self.pc + sign_extend(b_imm, 13))
            taken = False
            if   funct3 == 0: taken = regs[rs1] == regs[rs2]                                        # BEQ
            elif funct3 == 1: taken = regs[rs1] != regs[rs2]                                        # BNE
            elif funct3 == 4: taken = bool((regs[rs1] - regs[rs2]) >> 63)                           # BLT
            elif funct3 == 5: taken = not bool((regs[rs1] - regs[rs2]) >> 63)                       # BGE
            elif funct3 == 6: taken = regs[rs1] < regs[rs2]                                         # BLTU
            elif funct3 == 7: taken = regs[rs1] >= regs[rs2]                                        # BGEU
            self.Jump = taken
            result = limit16(self.jumpAddress if taken else 0)

        regs[0] = 0

        # Actualizare PC
        if self.Jump:
            self.pc = self.jumpAddress
        else:
            self.pc += 4

        print(f"[CPU] PC={self.pc:#06x}  result={result:#06x}")
        set_pins_from_result(result)

    def run(self):
        print("[CPU] Pornesc execuția...")
        while self.pc + 3 < len(self.memory):
            self.execute()
            if STEP_DELAY_MS > 0:
                time.sleep_ms(STEP_DELAY_MS)
        print("[CPU] Program terminat.")

cpu = RISCVProcessor()

while True:
    prog = receive_program()
    if prog is not None:
        cpu.load(prog)
        cpu.run()
    else:
        print("[PICO] Eroare recepție, aștept din nou...")
        time.sleep_ms(1000)

