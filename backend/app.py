# backend/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import logging

# Existing imports
from backend.mips_assembler import MipsAssembler
from backend.mips_disassembler import MipsDisassembler
# New import
from backend.mips_simulator import MipsSimulator

#logging.basicConfig(level=logging.DEBUG) # Use DEBUG for development
logger = logging.getLogger(__name__)

# Instantiate services
assembler = MipsAssembler()
disassembler = MipsDisassembler()
simulator = MipsSimulator() # Instantiate the simulator

app = Flask(__name__)
# Adjust CORS for your frontend origin if different
CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}})

@app.route('/')
def index():
    return "MIPS Simulator Backend is running!"

@app.route('/api/ping', methods=['GET'])
def ping():
    logging.debug("Ping endpoint called")
    return jsonify({"message": "pong"})

# --- Assemble/Disassemble Endpoints (keep as before) ---
@app.route('/api/assemble', methods=['POST'])
def handle_assemble():
    try:
        data = request.get_json()
        if not data or 'assembly' not in data:
            return jsonify({"errors": [{"message": "Missing 'assembly' key in request."}]}), 400
        assembly_code = data['assembly']
        logging.debug(f"Received assembly for assembly: {assembly_code[:100]}...")
        result = assembler.assemble(assembly_code)
        # Check for errors before logging potentially large successful result
        if result['errors']:
             logging.warning(f"Assembly failed: {result['errors']}")
        else:
             logging.debug(f"Assembly successful. Code length: {len(result['machine_code'])}, Data size: {len(result['data_segment'])//2} bytes")
        return jsonify(result)
    except Exception as e:
        logging.error(f"Error during assembly: {e}", exc_info=True)
        return jsonify({"errors": [{"message": f"Internal server error during assembly: {e}"}]}), 500

@app.route('/api/disassemble', methods=['POST'])
def handle_disassemble():
    try:
        data = request.get_json()
        if not data or 'machine_code' not in data or not isinstance(data['machine_code'], list):
             return jsonify({"errors": [{"message": "Missing/invalid 'machine_code' key (must be list of hex strings)."}]}), 400
        machine_code_lines = data['machine_code']
        logging.debug(f"Received machine code for disassembly: {machine_code_lines[:5]}") # Log first few lines
        result = disassembler.disassemble(machine_code_lines)
        logging.debug(f"Disassembly result: {result['assembly_code'][:100] if result else 'N/A'}...") # Log start of output
        return jsonify(result)
    except Exception as e:
        logging.error(f"Error during disassembly: {e}", exc_info=True)
        return jsonify({"errors": [{"message": f"Internal server error during disassembly: {e}"}]}), 500

# --- Simulation Endpoints ---

@app.route('/api/simulate/load', methods=['POST'])
def handle_simulate_load():
    """Loads assembled code and data into the simulator."""
    try:
        data = request.get_json()
        if not data or 'machine_code' not in data or 'data_segment' not in data:
             return jsonify({"error": "Missing 'machine_code' or 'data_segment' in request."}), 400

        # Assemble endpoint now returns list of {"hex":..., "bin":..., "dec":...}
        # We need just the hex values for loading
        machine_code_hex = [item['hex'] for item in data['machine_code']]
        data_segment_hex = data['data_segment']

        # TODO: Add options for base addresses if needed
        success = simulator.load_program(machine_code_hex, data_segment_hex)

        if success:
            logger.info("Program loaded into simulator successfully.")
            return jsonify(simulator.get_state())
        else:
             logger.error(f"Simulator failed to load program. Error: {simulator.error_message}")
             # Return the error state from the simulator
             return jsonify(simulator.get_state()), 400 # Bad request if load failed due to input

    except Exception as e:
        logger.error(f"Error during simulation load: {e}", exc_info=True)
        return jsonify({"error": f"Internal server error during simulation load: {e}"}), 500


@app.route('/api/simulate/step', methods=['POST'])
def handle_simulate_step():
    """Executes one step in the simulator."""
    try:
        if simulator.state not in ["loaded", "paused", "input_wait"]:
             return jsonify({"error": f"Simulator not in a state that can step (state={simulator.state})."}), 400

        logger.debug("Executing simulator step...")
        state = simulator.step()
        logger.debug(f"Step completed. New state: {state.get('state')}, PC: 0x{state.get('pc'):08x}")
        return jsonify(state)

    except Exception as e:
        logger.error(f"Error during simulation step: {e}", exc_info=True)
        # Try to return current simulator state even on internal error
        current_state = simulator.get_state()
        current_state["error"] = current_state.get("error") or f"Internal server error during step: {e}"
        return jsonify(current_state), 500


@app.route('/api/simulate/reset', methods=['POST'])
def handle_simulate_reset():
     """Resets the simulator to its initial state (before loading)."""
     # Note: This reset clears everything. The frontend would typically call /load again afterwards.
     try:
         logger.info("Resetting simulator.")
         simulator.reset()
         return jsonify(simulator.get_state())
     except Exception as e:
        logger.error(f"Error during simulation reset: {e}", exc_info=True)
        return jsonify({"error": f"Internal server error during simulation reset: {e}"}), 500

@app.route('/api/simulate/state', methods=['GET'])
def handle_simulate_get_state():
    """Gets the current state of the simulator without executing."""
    try:
        return jsonify(simulator.get_state())
    except Exception as e:
        logger.error(f"Error getting simulator state: {e}", exc_info=True)
        return jsonify({"error": f"Internal server error getting simulator state: {e}"}), 500

# --- Export Endpoints (Placeholder for Week 7) ---
@app.route('/api/export/asm', methods=['POST'])
def handle_export_asm():
     # TODO Week 7: Get assembly from request, return as file download
     return jsonify({"message": "Export ASM not implemented yet"}), 501

@app.route('/api/export/binary', methods=['POST'])
def handle_export_binary():
    # TODO Week 7: Get machine code from request, return as file download
    return jsonify({"message": "Export Binary not implemented yet"}), 501

# --- Example Loading (Placeholder for Week 7) ---
@app.route('/api/examples', methods=['GET'])
def handle_get_examples():
     # TODO Week 7: List available example files
     return jsonify({"examples": ["factorial.asm", "arraysum.asm"]}), 200 # Dummy data

@app.route('/api/examples/<filename>', methods=['GET'])
def handle_get_example_code(filename):
     # TODO Week 7: Read and return content of example file
     return jsonify({"filename": filename, "code": f"# Code for {filename} not loaded yet"}), 501


if __name__ == '__main__':
    # Set FLASK_APP=backend.app in environment or use this structure if running directly
    # Run with `python -m flask run --port 5001` from root directory after setting FLASK_APP
    app.run(debug=False, port=5001) # Turn debug off for default run, rely on logging