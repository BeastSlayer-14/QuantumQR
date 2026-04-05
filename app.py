from flask import Flask, request, jsonify
from flask_cors import CORS
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
import qrcode
import base64
from io import BytesIO
import os
from groq import Groq

app = Flask(__name__)
CORS(app)

groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def get_quantum_bit():
    sim = AerSimulator()
    qc = QuantumCircuit(1, 1)
    qc.h(0)
    qc.measure(0, 0)
    result = sim.run(qc, shots=1, memory=True).result()
    bit = result.get_memory()[0]
    return bit

def generate_bit_string(n: int) -> str:
    return "".join([get_quantum_bit() for _ in range(n)])

def generate_qr_base64(data: str) -> str:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=6,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")

@app.route("/run", methods=["POST"])
def run_circuit():
    data = request.get_json()
    n = int(data.get("n", 441))
    if n < 1 or n > 2048:
        return jsonify({"error": "n must be between 1 and 2048"}), 400
    try:
        bit_string = generate_bit_string(n)
        chat_url = "https://beastslayer-14.github.io/QuantumQR/#chat"
        qr_b64 = generate_qr_base64(chat_url)
        return jsonify({
            "bit_string": bit_string,
            "n": n,
            "zeros": bit_string.count('0'),
            "ones": bit_string.count('1'),
            "qr_image": qr_b64,
            "qr_url": chat_url
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    message = data.get("message", "")
    history = data.get("history", [])
    if not message:
        return jsonify({"error": "message is required"}), 400
    try:
        # Quantum encrypt user message
        key_bits = generate_bit_string(len(message))
        key_bytes = [int(b) for b in key_bits]
        encrypted_chars = [ord(ch) ^ (key_bytes[i % len(key_bytes)] * 42 + 7) for i, ch in enumerate(message)]
        encrypted_hex = ''.join(f'{c:04x}' for c in encrypted_chars)

        # Build Groq messages
        groq_messages = [{
            "role": "system",
            "content": (
                "You are a quantum AI assistant inside a quantum computing demo app. "
                "You know about quantum computing, QKD, and cryptography. "
                "Be helpful, concise, and occasionally reference the quantum-encrypted channel. "
                "Keep replies under 120 words."
            )
        }]
        for h in history:
            groq_messages.append({"role": h["role"], "content": h["content"]})
        groq_messages.append({"role": "user", "content": message})

        # Call Groq
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=groq_messages,
            max_tokens=512,
        )
        reply = response.choices[0].message.content

        # Quantum encrypt reply
        reply_key_bits = generate_bit_string(len(reply))
        reply_key_bytes = [int(b) for b in reply_key_bits]
        reply_encrypted_chars = [ord(ch) ^ (reply_key_bytes[i % len(reply_key_bytes)] * 42 + 7) for i, ch in enumerate(reply)]
        reply_encrypted_hex = ''.join(f'{c:04x}' for c in reply_encrypted_chars)

        return jsonify({
            "reply": reply,
            "user_encrypted": encrypted_hex,
            "user_key": key_bits,
            "reply_encrypted": reply_encrypted_hex,
            "reply_key": reply_key_bits,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
