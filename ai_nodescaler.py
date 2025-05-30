import os                      # For reading environment variables
import time                    # For adding delay between checks
import requests                # For querying Prometheus API
import urllib3                 # To suppress HTTPS warnings
from kubernetes import client, config         # Kubernetes Python client
from openshift.dynamic import DynamicClient   # For interacting with OpenShift APIs dynamically

# Suppress certificate warnings (since we use in-cluster CA cert)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --------------------- Configuration ---------------------

CPU_THRESHOLD = 0.6            # If CPU usage > 60%
MEM_THRESHOLD = 0.6            # If Memory usage > 60%
NODE_USAGE_LIMIT = 0.5         # Trigger scaling if 50% or more nodes are overloaded
CHECK_INTERVAL = 60            # Check every 60 seconds
MAX_REPLICAS = 10              # Do not scale beyond this number

# Prometheus query endpoint (inside OpenShift)
PROM_URL = "https://prometheus-k8s.openshift-monitoring.svc:9091/api/v1/query"

# These paths exist inside every pod with service account attached
TOKEN_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/token"
CA_CERT_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"

# MachineSet to scale (provided via environment variable)
MACHINESET_NAME = os.environ.get("MACHINESET_NAME")
NAMESPACE = "openshift-machine-api"

if not MACHINESET_NAME:
    raise ValueError("MACHINESET_NAME environment variable is not set")

# --------------------- Client Setup ---------------------

# Load Kubernetes config from inside the cluster
config.load_incluster_config()

# Create Kubernetes API client
k8s_client = client.ApiClient()

# Create dynamic OpenShift client
dyn_client = DynamicClient(k8s_client)

# --------------------- Prometheus Query Function ---------------------

def query_prometheus(query):
    """Query Prometheus API securely using the pod's service account token."""
    try:
        token = open(TOKEN_PATH).read()
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(PROM_URL, params={"query": query}, headers=headers, verify=CA_CERT_PATH)
        response.raise_for_status()
        return response.json()["data"]["result"]
    except Exception as e:
        print(f"[ERROR] Prometheus query failed: {e}")
        return []

# --------------------- Node Usage Fetching ---------------------

def get_node_usages():
    """Return CPU and memory usage for each node as fractions (0.0 - 1.0)."""
    cpu_query = '100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[2m])) * 100)'
    mem_query = '(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100'

    cpu_results = query_prometheus(cpu_query)
    mem_results = query_prometheus(mem_query)

    node_stats = {}
    for item in cpu_results:
        instance = item["metric"].get("instance", "")
        node_stats[instance] = {"cpu": float(item["value"][1]) / 100}

    for item in mem_results:
        instance = item["metric"].get("instance", "")
        if instance in node_stats:
            node_stats[instance]["mem"] = float(item["value"][1]) / 100

    return node_stats

# --------------------- Current Replicas ---------------------

def get_current_replicas():
    """Return the current number of replicas in the MachineSet."""
    try:
        ms_api = dyn_client.resources.get(api_version="machine.openshift.io/v1beta1", kind="MachineSet")
        ms = ms_api.get(name=MACHINESET_NAME, namespace=NAMESPACE)
        return ms.spec.replicas
    except Exception as e:
        print(f"[ERROR] Could not get current replicas: {e}")
        return None

# --------------------- Scale MachineSet ---------------------

def scale_machineset(new_replicas):
    """Scale the MachineSet to the desired number of replicas."""
    try:
        ms_api = dyn_client.resources.get(api_version="machine.openshift.io/v1beta1", kind="MachineSet")
        ms = ms_api.get(name=MACHINESET_NAME, namespace=NAMESPACE)
        ms.spec.replicas = new_replicas
        ms_api.patch(body=ms.to_dict(), name=MACHINESET_NAME, namespace=NAMESPACE)
        print(f"[INFO] Scaled MachineSet {MACHINESET_NAME} to {new_replicas} replicas")
    except Exception as e:
        print(f"[ERROR] Failed to scale MachineSet: {e}")

# --------------------- Main Scaling Logic ---------------------

def check_and_scale():
    """Main logic to check resource usage and scale if needed."""
    print("[INFO] Checking node usage...")
    node_stats = get_node_usages()

    if not node_stats:
        print("[WARNING] No node data. Skipping scaling.")
        return

    overloaded_nodes = [
        node for node, usage in node_stats.items()
        if usage.get("cpu", 0) > CPU_THRESHOLD and usage.get("mem", 0) > MEM_THRESHOLD
    ]

    total_nodes = len(node_stats)
    overloaded_count = len(overloaded_nodes)
    print(f"[INFO] {overloaded_count} of {total_nodes} nodes are overloaded.")

    if total_nodes == 0:
        print("[WARNING] No nodes found.")
        return

    if overloaded_count / total_nodes >= NODE_USAGE_LIMIT:
        current_replicas = get_current_replicas()
        if current_replicas is None:
            print("[ERROR] Cannot read current replica count.")
            return

        if current_replicas >= MAX_REPLICAS:
            print(f"[INFO] Already at or above MAX_REPLICAS ({MAX_REPLICAS}). Skipping scale.")
            return

        new_replicas = current_replicas + 1
        print(f"[INFO] Scaling from {current_replicas} to {new_replicas} replicas.")
        scale_machineset(new_replicas)
    else:
        print("[INFO] Cluster usage is within limits. No scaling needed.")

# --------------------- Loop Forever ---------------------

if __name__ == "__main__":
    print("[INFO] OpenShift Autoscaler agent started.")
    while True:
        try:
            check_and_scale()
        except Exception as e:
            print(f"[ERROR] Unexpected error: {e}")
        time.sleep(CHECK_INTERVAL)