import time
import threading
#Functie de extindere a unui numar la un numar specificat de biti
def sign_extend(number, bits):
    mask = (1 << bits) - 1
    
    sign_bit = number & (1 << (bits - 1))
    
    if sign_bit:
        return number | (~mask & 0xFFFFFFFFFFFFFFFF)
    else:
        return number
#Functie de trunchiere a unui numar la 64 de biti
def limit64bits(number):
    return number&0xFFFFFFFFFFFFFFFF
#Functie de trunchiere a unui numar la 16 de biti
def limit16bits(number):
    return number&0xFFFF

#Clasa principala            
class RISCVProcessor:
    #Constructorul clasei, se initializeaza registrele si memoria RAM
    def __init__(self):
        self.stop_event = threading.Event()
        self.reset()

    #Functia de reinitializare a registrelor si memoriei RAM
    def reset(self):
        self.pc = 0
        self.regdif = 0
        self.Jump = False
        self.jumpAddress = 0
        self.registers = [0] * 32
        self.dataMemory = [0] * 100
        #self.memory = [0] * 176
        self.instruction = 0
        self.opcode = 0
        self.funct3 = 0
        self.funct7 = 0
        self.imm12 = 0
        self.shamt = 0
        self.rs1 = 0
        self.rs2 = 0
        self.rd = 0
        self.result = 0
        self.stop_event.clear()

    def load_program(self,instructionBytes):
        self.memory=instructionBytes
                
    #Functia de preluare din memorie si de executare a unei instructiuni
    def execute(self):
        #Pentru a face o distinctie intre reinceperea programului, se afiseaza la consola un spatiu, informatie folosita la debug
        if(self.pc==0):
            print()
        #Preluarea instructiunii din ROM, in functie de valoarea registrului PC
        instruction = (self.memory[self.pc+3]<<24)+(self.memory[self.pc+2]<<16)+(self.memory[self.pc+1]<<8)+(self.memory[self.pc+0])
        #Decodificarea instructiunii in componente
        self.opcode = instruction & 0b1111111
        self.funct3 = (instruction >> 12) & 0b111
        self.funct7 = (instruction >> 25) & 0b1111111
        self.imm12 = (instruction >> 20) & 0b111111111111
        self.shamt = (instruction >> 20) & 0b11111
        self.rs1 = (instruction >> 15) & 0b11111
        self.rs2 = (instruction >> 20) & 0b11111
        self.rd = (instruction >> 7) & 0b11111
        #Executarea propriu-zisa a instructiunii, in functie de valorile decodificate
        if self.opcode == 0b0110011:  # Instructiuni de tip R

            if self.funct3 == 0b000:  # ADD, SUB
                if self.funct7 == 0b0000000: #ADD
                    self.registers[self.rd] = limit64bits(self.registers[self.rs1] + self.registers[self.rs2])
                    self.result=limit16bits(self.registers[self.rd])
                    print(f"PC: {hex(self.pc)}, result: {hex(self.result)}")
                elif self.funct7 == 0b0100000: #SUB
                    self.registers[self.rd] = limit64bits(self.registers[self.rs1] - self.registers[self.rs2])
                    self.result=limit16bits(self.registers[self.rd])
                    print(f"PC: {hex(self.pc)}, result: {hex(self.result)}")
            elif self.funct3 == 0b001:  # SLL
                self.registers[self.rd] = limit64bits(self.registers[self.rs1] << (self.registers[self.rs2]&0b11111))
                self.result=limit16bits(self.registers[self.rd])
                print(f"PC: {hex(self.pc)}, result: {hex(self.result)}")
            elif self.funct3 == 0b010:  # SLT
                self.regdif = limit64bits(self.registers[self.rs1] - self.registers[self.rs2])
                self.registers[self.rd] = int(self.regdif >> 63)
                self.result=limit16bits(self.registers[self.rd])
                print(f"PC: {hex(self.pc)}, result: {hex(self.result)}")
            elif self.funct3 == 0b011:  # SLTU
                self.registers[self.rd] = 1 if self.registers[self.rs1] < self.registers[self.rs2] else 0
                self.result=limit16bits(self.registers[self.rd])
                print(f"PC: {hex(self.pc)}, result: {hex(self.result)}")
            elif self.funct3 == 0b100:  # XOR
                self.registers[self.rd] = limit64bits(self.registers[self.rs1] ^ self.registers[self.rs2])
                self.result=limit16bits(self.registers[self.rd])
                print(f"PC: {hex(self.pc)}, result: {hex(self.result)}")
            elif self.funct3 == 0b101:
                if self.funct7 == 0b0000000:  # SRL
                    self.registers[self.rd] = limit64bits(self.registers[self.rs1] >> (self.registers[self.rs2]&0b11111))
                    self.result=limit16bits(self.registers[self.rd])
                    print(f"PC: {hex(self.pc)}, result: {hex(self.result)}")
                elif self.funct7 == 0b0100000:  # SRA
                    self.registers[self.rd] = limit64bits(self.registers[self.rs1] >> (self.registers[self.rs2]&0b11111))
                    self.result=limit16bits(self.registers[self.rd])
                print(f"PC: {hex(self.pc)}, result: {hex(self.result)}")
            elif self.funct3 == 0b110:  # OR
                self.registers[self.rd] = limit64bits(self.registers[self.rs1] | self.registers[self.rs2])
                self.result=limit16bits(self.registers[self.rd])
                print(f"PC: {hex(self.pc)}, result: {hex(self.result)}")
            elif self.funct3 == 0b111:  # AND
                self.registers[self.rd] = limit64bits(self.registers[self.rs1] & self.registers[self.rs2])
                self.result=limit16bits(self.registers[self.rd])
                print(f"PC: {hex(self.pc)}, result: {hex(self.result)}")
            else:
                self.result=0    
        elif self.opcode == 0b0010011:  # Instructiuni de tip I
            self.funct3 = self.funct3
            if self.funct3 == 0b000:  # ADDI
                self.registers[self.rd] = limit64bits(self.registers[self.rs1] +sign_extend(self.imm12,12))
                self.result=limit16bits(self.registers[self.rd])
                print(f"PC: {hex(self.pc)}, result: {hex(self.result)}")
            elif self.funct3 == 0b001:  # SLLI
                self.registers[self.rd] = limit64bits(self.registers[self.rs1] << self.shamt)
                self.result=limit16bits(self.registers[self.rd])
                print(f"PC: {hex(self.pc)}, result: {hex(self.result)}")
            elif self.funct3 == 0b010:  # SLTI
                self.registers[self.rd] = limit64bits(self.registers[self.rs1] - sign_extend(self.imm12,12))>>63
                self.result=limit16bits(self.registers[self.rd])
                print(f"PC: {hex(self.pc)}, result: {hex(self.result)}")
            elif self.funct3 == 0b011:  # SLTIU 
                self.registers[self.rd] = self.registers[self.rs1] < sign_extend(self.imm12,12)
                self.result=limit16bits(self.registers[self.rd])
                print(f"PC: {hex(self.pc)}, result: {hex(self.result)}")
            elif self.funct3 == 0b100:  # XORI
                self.registers[self.rd] = limit64bits(self.registers[self.rs1] ^ sign_extend(self.imm12,12))
                self.result=limit16bits(self.registers[self.rd])
                print(f"PC: {hex(self.pc)}, result: {hex(self.result)}")
            elif self.funct3 == 0b110:  # ORI
                self.registers[self.rd] = limit64bits(self.registers[self.rs1] | sign_extend(self.imm12,12))
                self.result=limit16bits(self.registers[self.rd])
                print(f"PC: {hex(self.pc)}, result: {hex(self.result)}")
            elif self.funct3 == 0b111:  # ANDI
                self.registers[self.rd] = limit64bits(self.registers[self.rs1] & sign_extend(self.imm12,12))
                self.result=limit16bits(self.registers[self.rd])
                print(f"PC: {hex(self.pc)}, result: {hex(self.result)}")
            elif self.funct3 == 0b101:  
                if self.funct7 == 0b0000000: #SRLI
                    self.registers[self.rd] = limit64bits(self.registers[self.rs1] >> self.shamt)
                    self.result=limit16bits(self.registers[self.rd])
                    print(f"PC: {hex(self.pc)}, result: {hex(self.result)}")
                elif self.funct7 == 0b0100000: #SRAI
                    self.registers[self.rd] = limit64bits(self.registers[self.rs1] >> self.shamt)
                    self.result=limit16bits(self.registers[self.rd])
                    print(f"PC: {hex(self.pc)}, result: {hex(self.result)}")
            else:
                self.result=0

        elif self.opcode == 0b0000011:  # Instructiuni Load

            if self.funct3 == 0b000:  # LB
                self.registers[self.rd]=sign_extend(self.dataMemory[limit64bits(self.registers[self.rs1]+sign_extend(self.imm12,12))]&0xff,8)
                self.result=limit16bits(self.registers[self.rd])
                print(f"PC: {hex(self.pc)}, result: {hex(self.result)}")
            elif self.funct3 == 0b001: #LH  
                self.registers[self.rd]=sign_extend(self.dataMemory[limit64bits(self.registers[self.rs1]+sign_extend(self.imm12,12))]&0xFFFF,16)
                self.result=limit16bits(self.registers[self.rd])
                print(f"PC: {hex(self.pc)}, result: {hex(self.result)}")
            elif self.funct3 == 0b010: #LW
                self.registers[self.rd]=sign_extend(self.dataMemory[limit64bits(self.registers[self.rs1]+sign_extend(self.imm12,12))]&0xFFFFFFFF,32)
                self.result=limit16bits(self.registers[self.rd])
                print(f"PC: {hex(self.pc)}, result: {hex(self.result)}")
            elif self.funct3 == 0b011: #LD
                self.registers[self.rd]=sign_extend(limit64bits(self.dataMemory[limit64bits(self.registers[self.rs1]+sign_extend(self.imm12,12))]),64)
                self.result=limit16bits(self.registers[self.rd])
                print(f"PC: {hex(self.pc)}, result: {hex(self.result)}")
            elif self.funct3 == 0b100: #LBU
                self.registers[self.rd]=self.dataMemory[limit64bits(self.registers[self.rs1]+sign_extend(self.imm12,12))]&0xFF
                self.result=limit16bits(self.registers[self.rd])
                print(f"PC: {hex(self.pc)}, result: {hex(self.result)}")
            elif self.funct3 == 0b101: #LHU
                self.registers[self.rd]=self.dataMemory[limit64bits(self.registers[self.rs1]+sign_extend(self.imm12,12))]&0xFFFF
                self.result=limit16bits(self.registers[self.rd])
                print(f"PC: {hex(self.pc)}, result: {hex(self.result)}")
            elif self.funct3 == 0b110: #LWU
                self.registers[self.rd]=self.dataMemory[limit64bits(self.registers[self.rs1]+sign_extend(self.imm12,12))]&0xFFFFFFFF
                self.result=limit16bits(self.registers[self.rd])
                print(f"PC: {hex(self.pc)}, result: {hex(self.result)}")
            else:
                self.result=0    
        elif self.opcode == 0b0100011:  # Instructiuni Store; Pentru aceste instructiuni, imm12 se calculeaza intr-un mod diferit
            if self.funct3== 0b000:  # SB 
                self.imm12=((instruction>>25)<<7)|((instruction>>7)&0b11111)
                self.dataMemory[limit64bits(self.registers[self.rs1]+sign_extend(self.imm12,12))]=self.registers[self.rs2]&0xff
                self.result=limit16bits(self.dataMemory[limit64bits(self.registers[self.rs1]+sign_extend(self.imm12,12))])
                print(f"PC: {hex(self.pc)}, result: {hex(self.result)}")
            elif self.funct3 == 0b001: #SH
                self.imm12=((instruction>>25)<<7)|((instruction>>7)&0b11111)
                self.dataMemory[limit64bits(self.registers[self.rs1]+sign_extend(self.imm12,12))]=self.registers[self.rs2]&0xFFFF
                self.result=limit16bits(self.dataMemory[limit64bits(self.registers[self.rs1]+sign_extend(self.imm12,12))])
                print(f"PC: {hex(self.pc)}, result: {hex(self.result)}")
            elif self.funct3 == 0b010: #SW
                self.imm12=((instruction>>25)<<7)|((instruction>>7)&0b11111)
                self.dataMemory[limit64bits(self.registers[self.rs1]+sign_extend(self.imm12,12))]=self.registers[self.rs2]&0xFFFFFFFF
                self.result=limit16bits(self.dataMemory[limit64bits(self.registers[self.rs1]+sign_extend(self.imm12,12))])
                print(f"PC: {hex(self.pc)}, result: {hex(self.result)}")
            elif self.funct3 == 0b011: #SD
                self.imm12=((instruction>>25)<<7)|((instruction>>7)&0b11111)
                self.dataMemory[limit64bits(self.registers[self.rs1]+sign_extend(self.imm12,12))]=self.registers[self.rs2]
                self.result=limit16bits(self.dataMemory[limit64bits(self.registers[self.rs1]+sign_extend(self.imm12,12))])
                print(f"PC: {hex(self.pc)}, result: {hex(self.result)}")
            else:
                self.result=0    
        elif self.opcode == 0b0110111:  # LUI
            self.imm12=instruction>>12
            self.registers[self.rd] = limit64bits(sign_extend(self.imm12,20) << 12)
            self.result=limit16bits(self.registers[self.rd])
            print(f"PC: {hex(self.pc)}, result: {hex(self.result)}")
        elif self.opcode == 0b0010111:  # AUIPC
            self.imm12=instruction>>12
            self.registers[self.rd] = limit64bits(self.pc+(sign_extend(self.imm12,20)<< 12))
            self.result=limit16bits(self.registers[self.rd])
            print(f"PC: {hex(self.pc)}, result: {hex(self.result)}")
        elif self.opcode == 0b1101111:  # JAL
            self.registers[self.rd] = limit64bits(self.pc+4)
            self.Jump=True
            self.imm12=(((instruction>>31)<<19)|(((instruction>>12)&0xFF)<<11)|(instruction>>21)&0x3FF)<<1
            self.jumpAddress=limit64bits(self.pc+sign_extend(self.imm12,20))
            self.result=limit16bits(self.jumpAddress)
            print(f"PC: {hex(self.pc)}, result: {hex(self.result)}")
        elif self.opcode == 0b1100111:  # JALR 
            self.registers[self.rd] = self.pc + 4
            self.Jump = True
            self.jumpAddress = limit64bits(self.registers[self.rs1] + sign_extend(self.imm12//2*2,12))
            self.result = self.jumpAddress
            self.result=limit16bits(self.jumpAddress)
            print(f"PC: {hex(self.pc)}, result: {hex(self.result)}")
        elif self.opcode == 0b1100011:#Instructiuni branch; pentru aceste tipuri de instructiuni, imm12 se calculeaza intr-un mod diferit
            self.imm12=((instruction>>31)<<12)|(((instruction>>7)&1)<<11)|(((instruction>>25)&0b111111)<<5)|((instruction>>8)&0xf)<<1
            if self.funct3 == 0b000: #BEQ
                self.Jump=(self.registers[self.rs1]==self.registers[self.rs2])
                self.jumpAddress=limit64bits(self.pc+sign_extend(self.imm12,12))
                self.result=limit16bits(self.jumpAddress if self.Jump else 0)
                print(f"PC: {hex(self.pc)}, result: {hex(self.result)}")
            elif self.funct3 == 0b001: #BNE
                self.Jump=(self.registers[self.rs1]!=self.registers[self.rs2])
                self.jumpAddress=limit64bits(self.pc+sign_extend(self.imm12,12))
                self.result=limit16bits(self.jumpAddress if self.Jump else 0)
                print(f"PC: {hex(self.pc)}, result: {hex(self.result)}")
            elif self.funct3 == 0b100: #BLT
                self.Jump=(self.registers[self.rs1]-self.registers[self.rs2])>>63
                self.jumpAddress=limit64bits(self.pc+sign_extend(self.imm12,12))
                self.result=limit16bits(self.jumpAddress if self.Jump else 0)
                print(f"PC: {hex(self.pc)}, result: {hex(self.result)}")
            elif self.funct3 == 0b101: #BGE
                self.Jump=1-((self.registers[self.rs1]-self.registers[self.rs2])>>63)
                self.jumpAddress=limit64bits(self.pc+sign_extend(self.imm12,12))
                self.result=limit16bits(self.jumpAddress if self.Jump else 0)
                print(f"PC: {hex(self.pc)}, result: {hex(self.result)}")
            elif self.funct3 == 0b110: #BLTU
                self.Jump=(self.registers[self.rs1]<self.registers[self.rs2])
                self.jumpAddress=limit64bits(self.pc+sign_extend(self.imm12,12))
                self.result=limit16bits(self.jumpAddress if self.Jump else 0)
                print(f"PC: {hex(self.pc)}, result: {hex(self.result)}")
            elif self.funct3 == 0b111: #BGEU
                self.Jump=(self.registers[self.rs1]>=self.registers[self.rs2])
                self.jumpAddress=limit64bits(self.pc+sign_extend(self.imm12,12))
                self.result=limit16bits(self.jumpAddress if self.Jump else 0)
                print(f"PC: {hex(self.pc)}, result: {hex(self.result)}")
            else:
                self.result=0
        else:
            self.result=0     
        #Verificarea flag-ului de salt   
        if self.Jump:
            self.pc = self.jumpAddress
            self.Jump = False
        else:
            self.pc += 4 
    def stop(self):
        self.stop_event.set()
    #Functia de executare a programului din memoria ROM
    def run(self):
        while self.pc<len(self.memory):
            if self.stop_event.is_set():
                return
            self.execute()
            time.sleep(2)
        
