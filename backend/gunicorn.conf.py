# Optimized Gunicorn configuration for minimal resource usage
import multiprocessing

# Server socket
import os
port = int(os.environ.get("PORT", 8000))
bind = f"0.0.0.0:{port}"
backlog = 2048

# Worker processes
workers = 2  # Optimal for 256MB-512MB RAM
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
preload_app = True  # Load data once, share between workers
timeout = 30
keepalive = 2

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "wattsup-backend"

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (if needed)
keyfile = None
certfile = None

# Memory optimization
worker_tmp_dir = "/dev/shm"  # Use RAM for temporary files
max_requests_jitter = 50  # Prevent all workers from restarting at once 