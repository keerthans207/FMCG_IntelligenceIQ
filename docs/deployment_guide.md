# Deployment Guide

## Remote Server Requirements

| Resource | Minimum | Recommended |
|---|---|---|
| OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |
| CPU | 2 vCPUs | 4 vCPUs |
| RAM | 4 GB | 8 GB |
| Disk | 50 GB | 100 GB |
| Network | SSH access | SSH + bandwidth for data transfer |

## Pinned Versions (Verified Compatible)

| Component | Version | Justification |
|---|---|---|
| OpenJDK | 17 (LTS) | Minimum for Spark 4.x; LTS support |
| Hadoop | 3.4.1 | Spark 4.0 is built against this version |
| Spark | 4.0.4 | Stable maintenance release, Java 17+ |
| MongoDB | 8.0 Community | Latest stable; Ubuntu 22.04 support |
| Python | 3.11 | Matches local; Spark 4.x minimum |
| PySpark | 4.0.4 | Matches Spark version |

## Installation Order

```bash
# 1. Clone the repository to the remote server
git clone <repo-url> /opt/fmcg-supplychainiq
cd /opt/fmcg-supplychainiq

# 2. Check the environment
bash scripts/remote/check_remote_environment.sh

# 3. Install Java 17
bash scripts/remote/install_java.sh
source ~/.bashrc

# 4. Install Hadoop
bash scripts/remote/install_hadoop.sh
source ~/.bashrc

# 5. Install Spark
bash scripts/remote/install_spark.sh
source ~/.bashrc

# 6. Install MongoDB
bash scripts/remote/install_mongodb.sh

# 7. Configure
bash scripts/remote/configure_hadoop.sh
bash scripts/remote/configure_spark.sh
bash scripts/remote/configure_mongodb.sh

# 8. Start services
bash scripts/remote/start_services.sh

# 9. Verify
bash scripts/remote/verify_services.sh

# 10. Create HDFS directories
bash scripts/remote/create_hdfs_dirs.sh

# 11. Deploy application (creates venv, installs deps, inits DB)
bash scripts/remote/deploy_application.sh

# 12. Run the pipeline
bash scripts/remote/run_pipeline.sh

# 13. Start API and dashboard (via SSH tunnel)
source /opt/fmcg-venv/bin/activate
uvicorn fmcg.api.main:app --host 0.0.0.0 --port 8000 &
streamlit run frontend/app.py --server.port 8501 &
```

## Accessing the Dashboard via SSH Tunnel

MongoDB, HDFS, and YARN management ports are NOT exposed publicly. Access the dashboard through an SSH tunnel:

```bash
# From your local machine:
ssh -L 8501:localhost:8501 -L 8000:localhost:8000 user@remote-server

# Then open in your browser:
# Dashboard: http://localhost:8501
# API docs:  http://localhost:8000/docs
```

## Stopping Services

```bash
bash scripts/remote/stop_services.sh
```

## Security Notes

- MongoDB binds to 127.0.0.1 only (not publicly exposed)
- HDFS/YARN management ports should be firewall-restricted
- Use SSH tunnels for private access
- Never commit .env files or credentials
- Restrict SSH access to your IP
- Enable MongoDB authentication for production deployments

## Estimated Costs (AWS EC2)

| Instance | vCPUs | RAM | Cost/hr | Monthly |
|---|---|---|---|---|
| t3.medium | 2 | 4 GB | ~$0.04 | ~$30 |
| t3.large | 2 | 8 GB | ~$0.08 | ~$60 |
| m5.large | 2 | 8 GB | ~$0.10 | ~$73 |

Storage: ~$0.10/GB/month for EBS (50 GB = ~$5/month)

**Do not create or start paid infrastructure without explicit approval.**
