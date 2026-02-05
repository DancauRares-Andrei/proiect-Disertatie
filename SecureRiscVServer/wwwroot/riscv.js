async function sendInstructions() {
    const textarea = document.getElementById('instr');
    const statusEl = document.getElementById('status');

    const lines = textarea.value
        .split('\n')
        .map(s => s.trim())
        .filter(s => s.length > 0);

    if (lines.length === 0) {
        statusEl.textContent = "❌ Please enter at least one instruction.";
        return;
    }

    // validare + normalizare
    const instructions = [];
    for (const line of lines) {
        let value;

        if (line.startsWith("0x") || line.startsWith("0X")) {
            value = parseInt(line, 16);
        } else {
            value = parseInt(line, 10);
        }

        if (Number.isNaN(value) || value < 0 || value > 0xFFFFFFFF) {
            statusEl.textContent = `❌ Invalid instruction: ${line}`;
            return;
        }

        instructions.push(
        line.startsWith("0x") ? line : "0x" + value.toString(16)
    );
        
    }
        instructions.push("0xFFFFFFFF");
    try {
        const response = await fetch("/api/crypto/program", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                instructions: instructions
            })
        });

        if (response.ok) {
            statusEl.textContent = `✅ Program sent (${instructions.length-1} instructions).`;
            textarea.value = "";
        } else {
            const text = await response.text();
            statusEl.textContent = `❌ Failed to send program: ${text}`;
        }
    } catch (err) {
        statusEl.textContent = "❌ Network error: " + err;
    }
}
