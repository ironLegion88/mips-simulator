# backend/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import os # For environment variables potentially

# Import backend modules using absolute path from package root
from backend.mips_assembler import MipsAssembler
from backend.mips_disassembler import MipsDisassembler
from backend.mips_simulator import MipsSimulator, MAX_STEPS

# Configure logging
# Use environment variable for log level, default to INFO
log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__) # Logger for this module

# Instantiate services (single instances shared across requests)
assembler = MipsAssembler()
disassembler = MipsDisassembler()
simulator = MipsSimulator() # Instantiate the MIPS simulator

# Create Flask app instance
app = Flask(__name__)

# Configure CORS (Cross-Origin Resource Sharing)
# Allow requests from the typical frontend development server origin
# In production, restrict this to the actual frontend domain
CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}})

# --- Basic Routes ---

@app.route('/')
def index():
    """Simple index route to confirm backend is running."""
    return "MIPS Simulator Backend is running!"

@app.route('/api/ping', methods=['GET'])
def ping():
    """Simple endpoint to check API connectivity."""
    logger.debug("Ping endpoint called")
    return jsonify({"message": "pong"})

# --- Assemble/Disassemble Endpoints ---

@app.route('/api/assemble', methods=['POST'])
def handle_assemble():
    """Handles assembly code input and returns machine code, errors, data segment, and address map."""
    try:
        data = request.get_json()
        # Basic input validation
        if not data or 'assembly' not in data:
            logger.warning("Assemble request missing 'assembly' key.")
            return jsonify({"errors": [{"message": "Missing 'assembly' key in request."}]}), 400

        assembly_code = data['assembly']
        logger.info(f"Received assembly request (length {len(assembly_code)} chars).")
        logger.debug(f"Assembly code snippet: {assembly_code[:100]}...")

        # Perform assembly using the assembler instance
        result = assembler.assemble(assembly_code)

        # Log success or failure
        if result['errors']:
             logger.warning(f"Assembly failed with {len(result['errors'])} errors.")
        else:
             logger.info(f"Assembly successful. Code length: {len(result['machine_code'])}, Data size: {len(result['data_segment'])//2} bytes")

        # Return the result (includes machine_code list, errors list, data_segment hex, address_map dict)
        return jsonify(result)

    except Exception as e:
        # Catch unexpected errors during assembly process
        logger.error(f"Unexpected error during assembly: {e}", exc_info=True)
        # Return a generic server error response
        return jsonify({"errors": [{"message": f"Internal server error during assembly: {e}"}]}), 500

@app.route('/api/disassemble', methods=['POST'])
def handle_disassemble():
    """Handles machine code hex lines and returns disassembled assembly code."""
    try:
        data = request.get_json()
        # Input validation
        if not data or 'machine_code' not in data or not isinstance(data['machine_code'], list):
             logger.warning("Disassemble request missing/invalid 'machine_code' key.")
             return jsonify({"errors": [{"message": "Missing/invalid 'machine_code' key (must be list of hex strings)."}]}), 400

        machine_code_lines = data['machine_code']
        logger.info(f"Received disassemble request for {len(machine_code_lines)} lines.")
        logger.debug(f"Disassemble input snippet: {machine_code_lines[:5]}")

        # Perform disassembly
        result = disassembler.disassemble(machine_code_lines)

        logger.info(f"Disassembly completed. Output lines: {result.get('assembly_code', '').count(chr(10)) + 1 if result.get('assembly_code') else 0}")
        # Return the result (includes assembly_code string, errors list)
        return jsonify(result)

    except Exception as e:
        # Catch unexpected errors
        logger.error(f"Unexpected error during disassembly: {e}", exc_info=True)
        return jsonify({"errors": [{"message": f"Internal server error during disassembly: {e}"}]}), 500

# --- Simulation Endpoints ---

@app.route('/api/simulate/load', methods=['POST'])
def handle_simulate_load():
    """Loads assembled code and data into the simulator instance."""
    try:
        data = request.get_json()
        # Validate input payload
        if not data or 'machine_code' not in data or 'data_segment' not in data:
             logger.warning("Simulate load request missing 'machine_code' or 'data_segment'.")
             return jsonify({"error": "Missing 'machine_code' or 'data_segment' in request."}), 400

        # Extract hex machine code from the structured input
        machine_code_hex = [item['hex'] for item in data['machine_code']]
        data_segment_hex = data['data_segment']
        logger.info(f"Received simulate load request. Code length: {len(machine_code_hex)}, Data size: {len(data_segment_hex)//2} bytes")

        # Call the simulator's load method
        # TODO: Add options for base addresses if needed in future
        success = simulator.load_program(machine_code_hex, data_segment_hex)

        if success:
            logger.info("Program loaded into simulator successfully.")
            # Return the initial state of the simulator
            return jsonify(simulator.get_state())
        else:
             # If loading failed (e.g., invalid hex format reported by simulator)
             logger.error(f"Simulator failed to load program. Error: {simulator.error_message}")
             # Return the simulator state (which should indicate 'error') and a 400 status
             return jsonify(simulator.get_state()), 400

    except Exception as e:
        # Catch unexpected errors during the loading process
        logger.error(f"Unexpected error during simulation load: {e}", exc_info=True)
        return jsonify({"error": f"Internal server error during simulation load: {e}"}), 500


@app.route('/api/simulate/step', methods=['POST'])
def handle_simulate_step():
    """Executes one step in the simulator."""
    try:
        # Check if the simulator is in a state that allows stepping
        if simulator.state not in ["loaded", "paused", "input_wait"]:
             logger.warning(f"Step request received but simulator state is '{simulator.state}'.")
             return jsonify({"error": f"Simulator not in a state that can step (state={simulator.state})."}), 400

        logger.debug("Executing simulator step...")
        # Execute the step and get the updated state
        state = simulator.step()
        logger.debug(f"Step completed. New state: {state.get('state')}, PC: 0x{state.get('pc'):08x}")
        # Return the complete updated state
        return jsonify(state)

    except Exception as e:
        # Catch unexpected errors during the step execution
        logger.error(f"Unexpected error during simulation step: {e}", exc_info=True)
        # Attempt to return the current simulator state even on internal error
        try:
            current_state = simulator.get_state()
            # Add or update error message in the state
            current_state["error"] = current_state.get("error") or f"Internal server error during step: {e}"
            current_state["state"] = "error" # Ensure state reflects error
            return jsonify(current_state), 500
        except Exception as inner_e:
            # If even getting state fails, return a minimal error
            logger.error(f"Failed to get simulator state after step error: {inner_e}", exc_info=True)
            return jsonify({"error": f"Internal server error during simulation step and state retrieval: {e}"}), 500

@app.route('/api/simulate/run', methods=['POST'])
def handle_simulate_run():
    """Runs the simulation until pause, finish, error, input needed, or step limit."""
    try:
        # Check if simulator can start running
        if simulator.state not in ["loaded", "paused"]:
             logger.warning(f"Run request received but simulator state is '{simulator.state}'.")
             return jsonify({"error": f"Simulator not in a state that can run (state={simulator.state})."}), 400

        # Extract optional step limit from request body (default to MAX_STEPS)
        data = request.get_json(silent=True)
        step_limit = MAX_STEPS # Default from simulator module
        if data and "steps" in data:
            try:
                 limit_req = int(data["steps"])
                 # Add a reasonable upper bound to requested steps if desired
                 step_limit = min(limit_req, MAX_STEPS * 10) # Allow up to 10x default via request
            except (ValueError, TypeError):
                 logger.warning(f"Invalid step limit '{data['steps']}' received, using default.")
                 pass # Ignore invalid limit, use default MAX_STEPS

        logger.info(f"Executing simulator run (limit: {step_limit} steps)...")
        # Execute the run method and get the final state after running
        final_state = simulator.run(step_limit=step_limit)
        logger.info(f"Run finished/paused. Final state: {final_state.get('state')}, PC: 0x{final_state.get('pc'):08x}")
        # Return the complete state after the run completes or pauses
        return jsonify(final_state)

    except Exception as e:
        # Catch unexpected errors during the run process
        logger.error(f"Unexpected error during simulation run: {e}", exc_info=True)
        try:
            current_state = simulator.get_state()
            current_state["error"] = current_state.get("error") or f"Internal server error during run: {e}"
            current_state["state"] = "error" # Ensure state reflects error
            return jsonify(current_state), 500
        except Exception as inner_e:
            # If even getting state fails, return a minimal error
            logger.error(f"Failed to get simulator state after run error: {inner_e}", exc_info=True)
            return jsonify({"error": f"Internal server error during simulation run and state retrieval: {e}"}), 500

@app.route('/api/simulate/pause', methods=['POST'])
def handle_simulate_pause():
    """Requests the simulator's run loop to pause."""
    try:
        logger.info("Received pause request.")
        simulator.request_pause()
        # Return the current state immediately (run loop will update state later)
        return jsonify(simulator.get_state())
    except Exception as e:
        logger.error(f"Unexpected error during simulation pause request: {e}", exc_info=True)
        return jsonify({"error": f"Internal server error during pause request: {e}"}), 500

@app.route('/api/simulate/provide_input', methods=['POST'])
def handle_simulate_provide_input():
    """Provides input data to the simulator when it's waiting."""
    try:
        data = request.get_json()
        if not data or 'input_data' not in data:
            logger.warning("Provide input request missing 'input_data' key.")
            return jsonify({"error": "Missing 'input_data' in request."}), 400

        if simulator.state != "input_wait":
            logger.warning("Provide input request received but simulator is not waiting for input.")
            return jsonify({"error": "Simulator is not currently waiting for input."}), 400

        input_data = str(data['input_data']) # Ensure it's a string
        logger.info(f"Received input data: '{input_data}'")

        success = simulator.provide_input(input_data)

        # Return the simulator state (which might indicate success, failure, or still waiting)
        state_after_input = simulator.get_state()
        status_code = 200 if success or state_after_input["state"] == "input_wait" else 400 # Use 400 if input was invalid format
        return jsonify(state_after_input), status_code

    except Exception as e:
        logger.error(f"Unexpected error during provide input: {e}", exc_info=True)
        try:
            current_state = simulator.get_state()
            current_state["error"] = current_state.get("error") or f"Internal server error providing input: {e}"
            # Don't necessarily set state to error, might recover
            return jsonify(current_state), 500
        except Exception as inner_e:
            logger.error(f"Failed to get simulator state after input error: {inner_e}", exc_info=True)
            return jsonify({"error": f"Internal server error during provide input and state retrieval: {e}"}), 500


@app.route('/api/simulate/reset', methods=['POST'])
def handle_simulate_reset():
     """Resets the simulator to its initial (empty) state."""
     try:
         logger.info("Resetting simulator state.")
         simulator.reset()
         # Return the freshly reset state
         return jsonify(simulator.get_state())
     except Exception as e:
        logger.error(f"Unexpected error during simulation reset: {e}", exc_info=True)
        return jsonify({"error": f"Internal server error during simulation reset: {e}"}), 500

@app.route('/api/simulate/state', methods=['GET'])
def handle_simulate_get_state():
    """Gets the current state of the simulator without executing."""
    try:
        logger.debug("Get simulator state request received.")
        # Return the current complete state
        return jsonify(simulator.get_state())
    except Exception as e:
        logger.error(f"Unexpected error getting simulator state: {e}", exc_info=True)
        return jsonify({"error": f"Internal server error getting simulator state: {e}"}), 500


# --- Export Endpoints (Placeholders for Week 7) ---
@app.route('/api/export/asm', methods=['POST'])
def handle_export_asm():
     # TODO Week 7: Accept assembly code in request, return as file download
     logger.warning("Export ASM endpoint called but not implemented.")
     return jsonify({"message": "Export ASM not implemented yet"}), 501 # 501 Not Implemented

@app.route('/api/export/binary', methods=['POST'])
def handle_export_binary():
    # TODO Week 7: Accept machine code list in request, format and return as file download
    logger.warning("Export Binary endpoint called but not implemented.")
    return jsonify({"message": "Export Binary not implemented yet"}), 501


# --- Example Loading (Placeholders for Week 7) ---
@app.route('/api/examples', methods=['GET'])
def handle_get_examples():
     # TODO Week 7: Scan a directory for .asm files and return list
     logger.debug("Get examples list endpoint called (returning dummy data).")
     return jsonify({"examples": ["factorial.asm", "arraysum.asm", "hello.asm"]}), 200 # Dummy data

@app.route('/api/examples/<filename>', methods=['GET'])
def handle_get_example_code(filename):
     # TODO Week 7: Read content of ../examples/{filename}.asm (sanitize filename!)
     logger.warning(f"Get example code endpoint called for '{filename}' (not implemented).")
     # Basic sanitization placeholder
     if ".." in filename or not filename.endswith(".asm"):
          return jsonify({"error": "Invalid filename"}), 400
     return jsonify({"filename": filename, "code": f"# Code for {filename} not loaded yet"}), 501


# --- Main execution for development server ---
if __name__ == '__main__':
    # Note: When running with `flask run`, Flask detects the 'app' instance.
    # This __main__ block is useful if you run `python backend/app.py` directly,
    # but setting FLASK_APP and using `flask run` is generally preferred.
    logger.info("Starting Flask development server...")
    # Use host='0.0.0.0' to make it accessible on the network if needed
    # Turn off debug mode for potentially better performance/stability during simulation runs
    app.run(debug=False, port=5001, host='127.0.0.1')