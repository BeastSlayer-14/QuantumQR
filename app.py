from flask import Flask, request, jsonify
from flask_cors import CORS
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
import qrcode
import base64
from io import BytesIO

app = Flask(__name__)
CORS(app)

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
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return encoded

@app.route("/run", methods=["POST"])
def run_circuit():
    data = request.get_json()
    n = int(data.get("n", 441))

    if n < 1 or n > 2048:
        return jsonify({"error": "n must be between 1 and 2048"}), 400

    try:
        bit_string = generate_bit_string(n)
        zeros = bit_string.count('0')
        ones  = bit_string.count('1')
        qr_b64 = generate_qr_base64(bit_string)

        return jsonify({
            "bit_string": bit_string,
            "n": n,
            "zeros": zeros,
            "ones": ones,
            "qr_image": qr_b64
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
