# AI-Powered NodeScaler for OpenShift 4.16+

An intelligent, AI-driven NodeScaler designed specifically for OpenShift clusters. It leverages simple yet effective AI models to predict CPU and memory usage trends, enabling proactive scaling of worker MachineSets. This approach helps maintain optimal cluster performance while minimizing manual intervention and resource wastage.

## Project Features

- Predictive scaling powered by Linear Regression forecasting.
- Seamless integration with OpenShift MachineSets API for dynamic worker node scaling.
- Configurable CPU and memory thresholds and scaling limits via environment variables.
- Lightweight Python implementation optimized for containerized deployment.

## Quickstart Highlights

- Build the autoscaler container image using the provided Dockerfile.
- Deploy the Kubernetes manifests to your OpenShift cluster.
- Adjust environment variables to customize scaling behavior.
- Monitor logs and cluster health to ensure smooth autoscaling operations.

**Note:** Before using this repository, please reach out to the repository owner on LinkedIn for further guidance.