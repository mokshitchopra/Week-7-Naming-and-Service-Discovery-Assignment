"""
Service Instance - A Flask microservice that registers itself with the
Service Registry on startup and exposes /hello and /health endpoints.
"""

import os
import time
import requests
from flask import Flask, jsonify

# Initialize the Flask application
app = Flask(__name__)

# Read configuration from environment variables (set in docker-compose.yml)
PORT = int(os.environ.get("PORT", 5001))           # Port this instance listens on
HOST_IP = os.environ.get("HOST_IP", "localhost")    # Docker service name for this instance
REGISTRY_URL = os.environ.get("REGISTRY_URL", "http://localhost:8500")  # URL of the service registry


def register_with_registry():
    """
    Register this service instance with the Service Registry.
    Uses retry logic because the registry container may not be ready
    when this service starts up.
    Retries up to 5 times with a 2-second delay between attempts.
    """
    # Build the registration payload
    payload = {
        "name": "service-a",     # Service name used for discovery
        "host": HOST_IP,         # Docker service name (e.g., "service-a-1")
        "port": PORT             # Port number this instance is running on
    }

    # Retry loop: attempt registration up to 5 times
    for attempt in range(1, 6):
        try:
            print(f"[SERVICE] Attempt {attempt}/5: Registering with registry at {REGISTRY_URL}/register ...")
            # Send POST request to the registry's /register endpoint
            response = requests.post(f"{REGISTRY_URL}/register", json=payload, timeout=5)

            # Check if registration was successful
            if response.status_code == 200:
                print(f"[SERVICE] Successfully registered as {HOST_IP}:{PORT}")
                return True
            else:
                print(f"[SERVICE] Registration failed with status {response.status_code}")
        except requests.exceptions.RequestException as e:
            # Handle connection errors (registry not ready yet)
            print(f"[SERVICE] Registration attempt {attempt} failed: {e}")

        # Wait 2 seconds before retrying
        if attempt < 5:
            print(f"[SERVICE] Retrying in 2 seconds...")
            time.sleep(2)

    # All attempts exhausted
    print("[SERVICE] WARNING: Could not register with the registry after 5 attempts!")
    return False


@app.route("/hello", methods=["GET"])
def hello():
    """
    Main endpoint for the service.
    Returns a JSON greeting with instance identification info.
    The client uses this to verify which instance handled the request.
    """
    return jsonify({
        "message": "Hello from Service A!",
        "instance": f"service-a-{PORT}",   # Unique instance identifier
        "host": HOST_IP,                    # Docker service name
        "port": PORT                        # Port number
    }), 200


@app.route("/health", methods=["GET"])
def health():
    """
    Health check endpoint.
    Returns HTTP 200 with status "ok" to indicate the service is running.
    """
    return jsonify({"status": "ok"}), 200


# Entry point: register with the registry, then start the Flask server
if __name__ == "__main__":
    # Register this instance before accepting requests
    register_with_registry()

    # Start the Flask server on the configured port, accessible from all interfaces
    print(f"[SERVICE] Starting service instance on {HOST_IP}:{PORT}")
    app.run(host="0.0.0.0", port=PORT)
