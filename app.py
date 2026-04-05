from flask import Flask, request, jsonify
from flask_cors import CORS
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
import qrcode, base64, anthropic
from io import BytesIO

app = Flask(__name__)
CORS(app)

def get_quantum_bit():
    sim = AerSimulator()
    qc = QuantumCircuit(1, 1)
    qc.h(0)
    qc.measure(0, 0)
    result = sim.run(qc, shots=1, memory=True).result()
    return result.get_memory()[0]

def generate_bit_string(n):
    return "".join([get_quantum_bit() for _ in range(n)])

def generate_qr_base64(data):
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=6, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")

def xor_encrypt(text, key):
    encrypted = [chr(ord(c) ^ int(key[i % len(key)])) for i, c in enumerate(text)]
    return base64.b64encode("".join(encrypted).encode("latin-1")).decode("utf-8")

@app.route("/run", methods=["POST"])
def run_circuit():
    data = request.get_json()
    n = int(data.get("n", 441))
    if n < 1 or n > 2048:
        return jsonify({"error": "n must be between 1 and 2048"}), 400
    try:
        bit_string = generate_bit_string(n)
        qr_b64 = generate_qr_base64(bit_string)
        return jsonify({"bit_string": bit_string, "n": n, "zeros": bit_string.count('0'), "ones": bit_string.count('1'), "qr_image": qr_b64})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    message = data.get("message", "")
    history = data.get("history", [])
    if not message:
        return jsonify({"error": "No message provided"}), 400
    try:
        key_length = max(len(message), 64)
        quantum_key = generate_bit_string(key_length)
        encrypted_input = xor_encrypt(message, quantum_key)

        claude_messages = [{"role": h["role"], "content": h["content"]} for h in history]
        claude_messages.append({"role": "user", "content": message})

        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            system="You are a quantum computing assistant embedded in a quantum-encrypted chat app. Be helpful and concise. Occasionally reference the quantum encryption. Keep responses under 150 words.",
            messages=claude_messages
        )
        reply = response.content[0].text

        reply_key_length = max(len(reply), 64)
        reply_quantum_key = generate_bit_string(reply_key_length)
        encrypted_reply = xor_encrypt(reply, reply_quantum_key)

        return jsonify({
            "reply": reply,
            "encrypted_input": encrypted_input,
            "encrypted_reply": encrypted_reply,
            "input_key": quantum_key,
            "reply_key": reply_quantum_key,
            "input_key_length": key_length,
            "reply_key_length": reply_key_length
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
