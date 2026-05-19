const REG_ALIAS = {
    zero: "x0",
    ra: "x1",
    sp: "x2",
    gp: "x3",
    tp: "x4",
    t0: "x5",
    t1: "x6",
    t2: "x7",
    s0: "x8",
    fp: "x8",
    s1: "x9",
    a0: "x10",
    a1: "x11",
    a2: "x12",
    a3: "x13",
    a4: "x14",
    a5: "x15",
    a6: "x16",
    a7: "x17",
    s2: "x18",
    s3: "x19",
    s4: "x20",
    s5: "x21",
    s6: "x22",
    s7: "x23",
    s8: "x24",
    s9: "x25",
    s10: "x26",
    s11: "x27",
    t3: "x28",
    t4: "x29",
    t5: "x30",
    t6: "x31"
};

function limit32bits(number) {
    return number & 0xFFFFFFFF;
}

function parseReg(r) {
    if (!r.startsWith("x")) r = REG_ALIAS[r];
    if (!r || !r.startsWith("x")) throw `Registru invalid: ${r}`;
    const v = parseInt(r.substring(1));
    if (v < 0 || v > 31) throw `Registru în afara ariei: ${r}`;
    return v;
}

function assembleLine(line) {
    const parts = line.replace(/,/g, "").split(/\s+/);
    const op = parts[0];

    // Funcție pentru parsare registru
    function parseReg(r) {
        if (!r.startsWith("x")) r = REG_ALIAS[r];
        if (!r || !r.startsWith("x")) throw `Registru invalid: ${r}`;
        const v = parseInt(r.substring(1));
        if (v < 0 || v > 31) throw `Registru în afara ariei: ${r}`;
        return v;
    }

    // Tip R (add, sub, and, or, xor, sll, srl, sra, sltu, slt)
    const R_OPS = {
        add: [0b0110011, 0b000, 0b0000000],
        sub: [0b0110011, 0b000, 0b0100000],
        and: [0b0110011, 0b111, 0b0000000],
        or: [0b0110011, 0b110, 0b0000000],
        xor: [0b0110011, 0b100, 0b0000000],
        sll: [0b0110011, 0b001, 0b0000000],
        srl: [0b0110011, 0b101, 0b0000000],
        sra: [0b0110011, 0b101, 0b0100000],
        slt: [0b0110011, 0b010, 0b0000000],
        sltu: [0b0110011, 0b011, 0b0000000]
    };

    // Tip I (addi, andi, ori, xori, slli, srli, srai, slti, sltiu)
    const I_OPS = {
        addi: [0b0010011, 0b000, 0b0000000],
        andi: [0b0010011, 0b111, 0b0000000],
        ori: [0b0010011, 0b110, 0b0000000],
        xori: [0b0010011, 0b100, 0b0000000],
        slti: [0b0010011, 0b010, 0b0000000],
        sltiu: [0b0010011, 0b011, 0b0000000],
        slli: [0b0010011, 0b001, 0b0000000],
        srli: [0b0010011, 0b101, 0b0000000],
        srai: [0b0010011, 0b101, 0b0100000]
    };

    // Load-uri
    const LOADS = {
        lb: 0,
        lh: 1,
        lw: 2,
        ld: 3,
        lbu: 4,
        lhu: 5,
        lwu: 6
    };
    // Store-uri
    const STORES = {
        sb: 0,
        sh: 1,
        sw: 2,
        sd: 3
    };
    // Branch-uri
    const BRANCH = {
        beq: 0,
        bne: 1,
        blt: 4,
        bge: 5,
        bltu: 6,
        bgeu: 7
    };
    // Jump-uri
    const JUMPS = ["jal", "jalr"];
    // Altele
    const OTHERS = ["lui", "auipc"];

    if (parts.length === 4) {
        // Tip R sau I cu 3 argumente
        if (op in R_OPS) {
            const rd = parseReg(parts[1]);
            const rs1 = parseReg(parts[2]);
            const rs2 = parseReg(parts[3]);
            const [opcode, funct3, funct7] = R_OPS[op];
            return opcode | (rd << 7) | (funct3 << 12) | (rs1 << 15) | (rs2 << 20) | (funct7 << 25);
        } else if (op in I_OPS) {
            const rd = parseReg(parts[1]);
            const rs1 = parseReg(parts[2]);
            let imm = parseInt(parts[3]);
            if (isNaN(imm)) throw `Valoare imediata invalida: ${parts[3]}`;
            if (imm < -2048 || imm > 2047) throw `Valoare imediata in afara limitei: ${imm}`;
            const [opcode, funct3, funct7] = I_OPS[op];
            return limit32bits(opcode | (rd << 7) | (funct3 << 12) | (rs1 << 15) | ((imm & 0xFFF) << 20) | (funct7 << 25));
        } else if (op in BRANCH) {
            const rs1 = parseReg(parts[1]);
            const rs2 = parseReg(parts[2]);
            let imm = parseInt(parts[3]);
            if (isNaN(imm)) throw `Valoare imediata invalida: ${parts[3]}`;
            if (imm < -2048 || imm > 2047) throw `Valoare imediata in afara limitei: ${imm}`;
            const opcode = 0b1100011;
            const funct3 = BRANCH[op];
            // codificare offset branch
            return opcode | (funct3 << 12) | (rs1 << 15) | (rs2 << 20) |
                (((imm >> 12) & 1) << 31) |
                (((imm >> 5) & 0x3F) << 25) |
                (((imm >> 1) & 0xF) << 8) |
                (((imm >> 11) & 1) << 7);
        }  else {
            throw `Instrucțiune nesuportată sau format invalid: ${line} ${BRANCH[op]}`;
        }
    }

    if (parts.length === 3) {
        if (op in LOADS) {
            const rd = parseReg(parts[1]);
            let offsetRs1 = parts[2].split("(");
            let imm = parseInt(offsetRs1[0]);
            const rs1 = parseReg(offsetRs1[1].replace(")", ""));
            if (isNaN(imm)) throw `Valoare imediata invalida: ${offsetRs1[0]}`;
            const opcode = 0b0000011;
            const funct3 = LOADS[op];
            return limit32bits(opcode | (rd << 7) | (funct3 << 12) | (rs1 << 15) | ((imm & 0xFFF) << 20));
        }
        else if (op in STORES) {
            // rs2 este primul argument
            const rs2 = parseReg(parts[1]);

            // al doilea argument: offset(rs1)
            let offsetRs1 = parts[2].match(/^(-?\d+)\((\w+)\)$/);
            if (!offsetRs1) throw `Format invalid pentru store: ${parts[2]}`;
            let imm = parseInt(offsetRs1[1]);
            const rs1 = parseReg(offsetRs1[2]);
            if (isNaN(imm)) throw `Valoare imediata invalida: ${offsetRs1[1]}`;

            const opcode = 0b0100011;
            const funct3 = STORES[op];

            // codificare tip S
            return limit32bits(opcode |
                ((imm & 0x1F) << 7) | // imm[4:0]
                (funct3 << 12) |
                (rs1 << 15) |
                (rs2 << 20) |
                (((imm >> 5) & 0x7F) << 25)); // imm[11:5]
        }
        else if (OTHERS.includes(op)) {
            const rd = parseReg(parts[1]);
            let imm = parseInt(parts[2]);
            if (isNaN(imm)) throw `Valoare imediata invalida: ${parts[2]}`;
            const opcode = op === "lui" ? 0b0110111 : 0b0010111;
            return opcode | (rd << 7) | ((imm & 0xFFFFF) << 12);
        } else if (JUMPS.includes(op)) {
            const rd = parseReg(parts[1]);
            if (op === "jal") {
                let imm = parseInt(parts[2]);
                if (isNaN(imm)) throw `Valoare imediata invalida: ${parts[2]}`;
                const opcode = 0b1101111;
                return limit32bits(opcode | (rd << 7) |
                    (((imm >> 20) & 1) << 31) |
                    (((imm >> 1) & 0x3FF) << 21) |
                    (((imm >> 11) & 1) << 20) |
                    (((imm >> 12) & 0xFF) << 12));
            } else if (op === "jalr") {
                let offsetRs1 = parts[2].split("(");
                let imm = parseInt(offsetRs1[0]);
                const rs1 = parseReg(offsetRs1[1].replace(")", ""));
                const opcode = 0b1100111;
                return limit32bits(opcode | (rd << 7) | (rs1 << 15) | ((imm & 0xFFF) << 20));
            }
        }
    }

    throw `Format sau instrucțiune nesuportată: ${line} ${op} ${parts.length}`;
}


async function sendInstructions() {
    const textarea = document.getElementById("instr");
    const statusEl = document.getElementById("status");

    const lines = textarea.value
    .split("\n")
    .map(l => l.trim())
    .filter(l => l.length > 0 && !l.startsWith("#"));

    if (lines.length === 0) {
        statusEl.textContent = "❌ Va rog să introduceți cel puțin o instrucțiune!";
        return;
    }

    let machine = [];

    try {
        for (const line of lines) {
            const encoded = assembleLine(line);
            machine.push("0x" + (encoded >>> 0).toString(16).padStart(8, "0"));
        }
    } catch (err) {
        statusEl.textContent = "❌ " + err;
        return;
    }
    //terminator
    machine.push("0xFFFFFFFF");
    const token = sessionStorage.getItem("token");
    const response = await fetch("/api/crypto/program", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + token
        },
        body: JSON.stringify({
            instructions: machine
        })
    });

    if (response.ok) {
        statusEl.textContent = `✅ Program trimis (${machine.length - 1} instrucțiuni).`;
    } else {
        statusEl.textContent = "❌ Eroare server.";
    }
}
