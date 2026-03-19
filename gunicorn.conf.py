# gunicorn.conf.py
bind         = "127.0.0.1:8081"
workers      = 4
worker_class = "uvicorn.workers.UvicornWorker"
accesslog    = "-"
errorlog     = "-"
loglevel     = "info"
max_requests        = 1000
max_requests_jitter = 100
timeout      = 120
keepalive    = 5
