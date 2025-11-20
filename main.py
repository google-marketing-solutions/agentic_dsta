"""Main file for the DSTA project."""

import os
from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route('/')
def home():
    """Health check and welcome message."""
    return jsonify({"message": "Welcome to agentic_dsta API"})

@app.route('/api/v1/dsta', methods=['POST'])
def process_dsta_request():
    """
    Placeholder endpoint for handling DSTA agent requests.
    Expects a JSON body with a 'prompt'.
    """
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    prompt = data.get("prompt")
    session_id = data.get("session_id")

    if not prompt:
        return jsonify({"error": "Missing 'prompt' in request body"}), 400

    print(f"Received prompt: {prompt}, session_id: {session_id}")

    # TODO: Implement the actual agent logic here
    # This is where you would call your agent, interact with services, etc.
    # Load configurations and secrets securely, e.g., from environment variables.
    # Example: api_key = os.environ.get("MY_API_KEY")

    # Placeholder response
    response_message = f"Processing prompt: {prompt}"
    if session_id:
        response_message += f" for session: {session_id}"

    return jsonify({
        "response": response_message,
        "session_id": session_id
    })

if __name__ == '__main__':
    # Reads the PORT environment variable, defaulting to 8080
    port = int(os.environ.get("PORT", 8080))
    # Bind to 0.0.0.0 to be accessible from outside the container
    app.run(debug=True, host='0.0.0.0', port=port)
