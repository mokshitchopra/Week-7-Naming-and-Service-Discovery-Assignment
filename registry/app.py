"""
Service Registry - A simple in-memory service registry built with Flask.
Services register themselves here, and clients discover available instances
by querying this registry.
"""

from flask import Flask, request, jsonify

# Initialize the Flask application
app = Flask(__name__)

# In-memory registry: maps service names to lists of instance dicts
# Example: {"service-a": [{"host": "service-a-1", "port": 5001}, {"host": "service-a-2", "port": 5002}]}
registry = {}


@app.route("/register", methods=["POST"])
def register():
    """
    Register a new service instance.
    Expects JSON body: {"name": "service-a", "host": "service-a-1", "port": 5001}
    Stores the instance in the registry under the given service name.
    Prevents duplicate registrations for the same host:port combo.
    """
    # Parse the incoming JSON payload
    data = request.get_json()

    # Extract fields from the request
    name = data.get("name")       # e.g. "service-a"
    host = data.get("host")       # e.g. "service-a-1" (Docker service name)
    port = data.get("port")       # e.g. 5001

    # Initialize the list for this service name if it doesn't exist yet
    if name not in registry:
        registry[name] = []

    # Build the instance info dict
    instance = {"host": host, "port": port}

    # Avoid duplicate registrations (same host and port)
    if instance not in registry[name]:
        registry[name].append(instance)
        print(f"[REGISTRY] Registered instance: {name} at {host}:{port}")
    else:
        print(f"[REGISTRY] Instance already registered: {name} at {host}:{port}")

    # Return a success response
    return jsonify({"status": "registered"}), 200


@app.route("/discover/<service_name>", methods=["GET"])
def discover(service_name):
    """
    Discover all registered instances for a given service name.
    Returns JSON: {"instances": [{"host": "...", "port": ...}, ...]}
    If the service name is not found, returns an empty list.
    """
    # Look up instances for the requested service name, default to empty list
    instances = registry.get(service_name, [])
    print(f"[REGISTRY] Discovery request for '{service_name}': {len(instances)} instance(s) found")
    return jsonify({"instances": instances}), 200


@app.route("/services", methods=["GET"])
def services():
    """
    Debug endpoint: returns the entire registry dictionary.
    Useful for inspecting all registered services and their instances.
    """
    print(f"[REGISTRY] Full registry requested. Total services: {len(registry)}")
    return jsonify(registry), 200


# Run the Flask app on port 8500, accessible from all network interfaces
if __name__ == "__main__":
    print("[REGISTRY] Starting Service Registry on port 8500...")
    app.run(host="0.0.0.0", port=8500)
