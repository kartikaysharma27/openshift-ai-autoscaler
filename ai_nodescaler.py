import os
import time
import requests
import urllib3
import numpy as np
from collections import deque
from sklearn.linear_model import LinearRegression
from kubernetes import client, config
from openshift.dynamic import DynamicClient
from prometheus_client import start_http_server, Summary

# Disable insecure HTTPS warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Environment configs
CPU_THRESHOLD = float(os.getenv("CPU_THRESHOLD", "0.6"))
MEM_THRESHOLD = float(os.getenv("MEM_THRESHOLD", "0.6"))
NODE_USAGE_LIMIT = float(os.getenv("NODE_USAGE_LIMIT", "0.5"))
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "60"))
MAX_REPLICAS = int(os.getenv("MAX_REPLICAS", "10"))
PROM_URL = os.getenv(
    "PROM_URL",
    "https://prometheus-k8s.openshift-monitoring.svc:9091/api/v1/query"
)

TOKEN_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/token"
CA_CERT_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
NAMESPACE = "openshift-machine-api"

config.load_incluster_config()
k8s_client = client.ApiClient()
dyn_client = DynamicClient(k8s_client)

# Healthy file for probes
with open("/tmp/healthy", "w") as f:
    f.write("ok")

# Prometheus metrics
REQUEST_TIME = Summary('autoscaler_check_duration_seconds', 'Time spent checking and scaling')

# AI prediction window
history_window = 5
cpu_history = deque(maxlen=history_window)
mem_history = deque(maxlen=history_window)

def predict_next(values):
    try:
        if len(values) < 2:
            return values[-1] if values else 0
        X = np.array(range(len(values))).reshape(-1, 1)
        y = np.array(values)
        model = LinearRegression().fit(X, y)
        return float(model.predict([[len(values)]]))
    except Exception as e:
        print(f"[ERROR] AI Prediction failed: {e}")
        return values[-1] if values else 0

def query_prometheus(query):
    try:
        token = open(TOKEN_PATH).read()
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(PROM_URL, params={"query": query}, headers=headers, verify=CA_CERT_PATH)
        response.raise_for_status()
        return response.json()["data"]["result"]
    except Exception as e:
        print(f"[ERROR] Prometheus query failed: {e}")
        return []

def get_node_usages():
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
        else:
            print(f"[WARN] Memory data missing for node instance {instance}")

    return node_stats

def get_worker_machinesets():
    ms_api = dyn_client.resources.get(api_version="machine.openshift.io/v1beta1", kind="MachineSet")
    return [
        ms for ms in ms_api.get(namespace=NAMESPACE).items
        if ms.metadata.labels.get("machine.openshift.io/cluster-api-machine-role") == "worker"
    ]

def get_current_replicas(ms):
    return ms.spec.replicas

def scale_machineset(ms, new_replicas):
    ms_api = dyn_client.resources.get(api_version="machine.openshift.io/v1beta1", kind="MachineSet")
    ms.spec.replicas = new_replicas
    ms_api.patch(body=ms.to_dict(), name=ms.metadata.name, namespace=NAMESPACE)
    print(f"[INFO] Scaled MachineSet {ms.metadata.name} to {new_replicas} replicas")

@REQUEST_TIME.time()
def check_and_scale():
    print("[INFO] Checking node usage...")
    node_stats = get_node_usages()
    if not node_stats:
        print("[WARNING] No node stats available. Skipping.")
        return

    avg_cpu = np.mean([v["cpu"] for v in node_stats.values()])
    avg_mem = np.mean([v.get("mem", 0) for v in node_stats.values()])

    cpu_history.append(avg_cpu)
    mem_history.append(avg_mem)

    predicted_cpu = min(1.0, max(0, predict_next(list(cpu_history))))
    predicted_mem = min(1.0, max(0, predict_next(list(mem_history))))

    print(f"[INFO] Avg CPU: {avg_cpu:.2f}, Avg MEM: {avg_mem:.2f}")
    print(f"[AI] Predicted CPU: {predicted_cpu:.2f}, Predicted MEM: {predicted_mem:.2f}")

    if predicted_cpu > CPU_THRESHOLD and predicted_mem > MEM_THRESHOLD:
        for ms in get_worker_machinesets():
            current = get_current_replicas(ms)
            if current < MAX_REPLICAS:
                new = current + 1
                scale_machineset(ms, new)
    else:
        print("[INFO] Cluster usage is within limits. No scaling proceeding.")

if __name__ == "__main__":
    print("[INFO] OpenShift AI-Powered Autoscaler started.")
    start_http_server(8000)
    while True:
        try:
            check_and_scale()
        except Exception as e:
            print(f"[ERROR] Unexpected error: {e}")
        time.sleep(CHECK_INTERVAL)