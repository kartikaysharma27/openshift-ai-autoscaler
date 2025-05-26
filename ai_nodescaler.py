import requests
import time
import subprocess
CPU_THRESHOLD = 0.6
MEM_THRESHOLD = 0.6
TRIGGER_PERCENT = 0.5
CHECK_INTERVAL = 60
PROM_URL = "http://prometheus-k8s.openshift-monitoring.svc:9090/api/v1/query"
MACHINESET_NAME = "your-machineset-name"  # Update this
NAMESPACE = "openshift-machine-api"

def query_prometheus(query):
    try:
        response = requests.get(PROM_URL, params={'query': query})
        result = response.json()
        return result['data']['result']
    except Exception as e:
        print(f"Error querying Prometheus: {e}")
        return []

def get_node_usages():
    cpu_query = '100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[2m])) * 100)'
    mem_query = '(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100'
    cpu_usages = query_prometheus(cpu_query)
    mem_usages = query_prometheus(mem_query)
    node_stats = {}
    for item in cpu_usages:
        node = item['metric']['instance']
        node_stats[node] = {'cpu': float(item['value'][1]) / 100}
    for item in mem_usages:
        node = item['metric']['instance']
        if node in node_stats:
            node_stats[node]['mem'] = float(item['value'][1]) / 100
    return node_stats

def scale_nodes():
    print("Checking node usage...")
    stats = get_node_usages()
    overloaded = [
        node for node, usage in stats.items()
        if usage.get("cpu", 0) > CPU_THRESHOLD and usage.get("mem", 0) > MEM_THRESHOLD
    ]
    if len(overloaded) / len(stats) >= TRIGGER_PERCENT:
        print(f"{len(overloaded)} of {len(stats)} nodes overloaded. Scaling up...")
        scale_cmd = [
            "oc", "scale", "machineset", MACHINESET_NAME,
            "-n", NAMESPACE, "--replicas=3"
        ]
        subprocess.run(scale_cmd)
    else:
        print("Load is normal. No scaling needed.")

if __name__ == "__main__":
    while True:
        scale_nodes()
        time.sleep(CHECK_INTERVAL)