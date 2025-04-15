# backend/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import logging

# Import the new classes using backend prefix
from backend.mips_assembler import MipsAssembler
from backend.mips_disassembler import MipsDisassembler

logging.basicConfig(level=logging.DEBUG)

# Instantiate assembler and disassembler (can be reused)
assembler = MipsAssembler()
disassembler = MipsDisassembler()

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}}) # Adjust origin for production

@app.route('/')
def index():
    return "MIPS Simulator Backend is running!"

@app.route('/api/ping', methods=['GET'])
def ping():
    logging.debug("Ping endpoint called")
    return jsonify({"message": "pong"})

@app.route('/api/assemble', methods=['POST'])
def handle_assemble():
    try:
        data = request.get_json()
        if not data or 'assembly' not in data:
            return jsonify({"errors": [{"message": "Missing 'assembly' key in request."}]}), 400

        assembly_code = data['assembly']
        logging.debug(f"Received assembly for assembly: {assembly_code[:100]}...")
        # Use the assembler instance
        result = assembler.assemble(assembly_code)
        logging.debug(f"Assembly result: {result}")
        return jsonify(result)
    except Exception as e:
        logging.error(f"Error during assembly: {e}", exc_info=True)
        return jsonify({"errors": [{"message": f"Internal server error during assembly: {e}"}]}), 500

@app.route('/api/disassemble', methods=['POST'])
def handle_disassemble():
    try:
        data = request.get_json()
        if not data or 'machine_code' not in data:
             return jsonify({"errors": [{"message": "Missing 'machine_code' key in request."}]}), 400
        if not isinstance(data['machine_code'], list):
             return jsonify({"errors": [{"message": "'machine_code' must be a list of hex strings."}]}), 400

        machine_code_lines = data['machine_code']
        logging.debug(f"Received machine code for disassembly: {machine_code_lines}")
        # Use the disassembler instance
        result = disassembler.disassemble(machine_code_lines)
        logging.debug(f"Disassembly result: {result}")
        return jsonify(result)
    except Exception as e:
        logging.error(f"Error during disassembly: {e}", exc_info=True)
        return jsonify({"errors": [{"message": f"Internal server error during disassembly: {e}"}]}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5001)