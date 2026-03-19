"""
Service Registry - A simple in-memory service registry built with Flask.
Services register themselves here, and clients discover available instances
by querying this registry.

Includes TTL-based eviction: instances that haven't sent a heartbeat
within TTL seconds are automatically removed from the registry.
"""

import time
import threading
from flask import Flask, request, jsonify

# Initialize the Flask application
app = Flask(__name__)

# In-memory registry: maps service names to a list of instance dicts
# Each instance includes a "last_seen" timestamp for TTL eviction
# Example: {"service-a": [{"host": "service-a-1", "port": 5001, "last_seen": 1710000000.0}]}
registry = {}

# Time-to-live in seconds — instances not refreshed within this window are evicted
TTL = 30


# ── Background eviction thread ────────────────────────────────────────────────
def evict_stale():
    """
    Background thread that runs every 5 seconds and removes instances
    whose last_seen timestamp is older than TTL seconds ago.
    This ensures that stopped/crashed instances are automatically
    cleaned out of the registry.
    """
    while True:
        now = time.time()
        for name in list(registry.keys()):
            before = len(registry[name])
            registry[name] = [
                i for i in registry[name]
                if now - i.get("last_seen", 0) < TTL
            ]
            evicted = before - len(registry[name])
            if evicted > 0:
                print(f"[REGISTRY] Evicted {evicted} stale instance(s) from '{name}'")
        time.sleep(5)  # check every 5 seconds


# Start the eviction thread as a daemon (dies when main thread exits)
threading.Thread(target=evict_stale, daemon=True).start()


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.route("/register", methods=["POST"])
def register():
    """
    Register a new service instance or refresh an existing one.
    Expects JSON body: {"name": "service-a", "host": "service-a-1", "port": 5001}
    - If the instance already exists, updates its last_seen timestamp (heartbeat).
    - If it's new, adds it to the registry.
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

    # Check if this instance is already registered — if so, refresh its timestamp
    for instance in registry[name]:
        if instance["host"] == host and instance["port"] == port:
            instance["last_seen"] = time.time()
            return jsonify({"status": "refreshed"}), 200

    # New instance — add it to the registry with a timestamp
    registry[name].append({"host": host, "port": port, "last_seen": time.time()})
    print(f"[REGISTRY] Registered instance: {name} at {host}:{port}")

    return jsonify({"status": "registered"}), 200


@app.route("/discover/<service_name>", methods=["GET"])
def discover(service_name):
    """
    Discover all live instances for a given service name.
    Only returns instances whose last_seen is within the TTL window.
    Returns JSON: {"instances": [{"host": "...", "port": ...}, ...]}
    """
    now = time.time()
    # Filter to only instances seen within TTL, and strip internal fields
    instances = [
        {"host": i["host"], "port": i["port"]}
        for i in registry.get(service_name, [])
        if now - i.get("last_seen", 0) < TTL
    ]
    print(f"[REGISTRY] Discovery request for '{service_name}': {len(instances)} live instance(s)")
    return jsonify({"instances": instances}), 200


@app.route("/services", methods=["GET"])
def services():
    """
    Debug endpoint: returns the entire registry dictionary.
    Strips internal fields (last_seen) for clean output.
    """
    clean = {
        name: [{"host": i["host"], "port": i["port"]} for i in instances]
        for name, instances in registry.items()
    }
    print(f"[REGISTRY] Full registry requested. Total services: {len(registry)}")
    return jsonify(clean), 200


# Run the Flask app on port 8500, accessible from all network interfaces
if __name__ == "__main__":
    print("[REGISTRY] Starting Service Registry on port 8500 (TTL={TTL}s)...")
    app.run(host="0.0.0.0", port=8500)
