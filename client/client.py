"""
Service Discovery Client - Continuously discovers service instances from the
registry and calls a randomly chosen instance's /hello endpoint.
"""

import os
import time
import random
import requests

# Read configuration from environment variables (set in docker-compose.yml)
REGISTRY_URL = os.environ.get("REGISTRY_URL", "http://localhost:8500")  # URL of the service registry
SERVICE_NAME = os.environ.get("SERVICE_NAME", "service-a")              # Name of the service to discover

# Polling interval in seconds
POLL_INTERVAL = 3


def main():
    """
    Main loop: every 3 seconds, discover instances and call one at random.
    Runs indefinitely. Handles all exceptions to prevent crashing.
    """
    print(f"[CLIENT] Starting client. Registry: {REGISTRY_URL}, Service: {SERVICE_NAME}")
    print(f"[CLIENT] Polling every {POLL_INTERVAL} seconds...\n")

    while True:
        try:
            # ----- Step 1: Discover instances from the registry -----
            discover_url = f"{REGISTRY_URL}/discover/{SERVICE_NAME}"
            print(f"[DISCOVERY] Querying registry: {discover_url}")

            # Send GET request to the registry's /discover endpoint
            response = requests.get(discover_url, timeout=5)
            data = response.json()

            # Parse the list of instances from the response
            instances = data.get("instances", [])
            print(f"[DISCOVERY] Total instances found: {len(instances)}")

            # ----- Step 2: Check if any instances are available -----
            if not instances:
                print("[DISCOVERY] WARNING: No instances found! Retrying in 3 seconds...\n")
                time.sleep(POLL_INTERVAL)
                continue

            # ----- Step 3: Randomly select one instance -----
            chosen = random.choice(instances)
            chosen_host = chosen["host"]
            chosen_port = chosen["port"]
            print(f"[DISCOVERY] Randomly selected instance: {chosen_host}:{chosen_port}")

            # ----- Step 4: Call the chosen instance's /hello endpoint -----
            service_url = f"http://{chosen_host}:{chosen_port}/hello"
            print(f"[CALL] Calling: {service_url}")

            # Send GET request to the selected service instance
            service_response = requests.get(service_url, timeout=5)
            result = service_response.json()

            # ----- Step 5: Print the full response -----
            print(f"[RESPONSE] {result}\n")

        except requests.exceptions.ConnectionError as e:
            # Handle case where registry or service instance is unreachable
            print(f"[ERROR] Connection error: {e}\n")
        except requests.exceptions.Timeout:
            # Handle request timeout
            print(f"[ERROR] Request timed out\n")
        except Exception as e:
            # Catch-all for any unexpected errors — keeps the client running
            print(f"[ERROR] Unexpected error: {e}\n")

        # Wait before the next polling cycle
        time.sleep(POLL_INTERVAL)


# Entry point
if __name__ == "__main__":
    main()
