FROM registry-vpc.cn-shanghai.aliyuncs.com/opple-iot/python:3.11-slim-bookworm

WORKDIR /app

RUN sed -i 's|http://deb.debian.org|https://mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources
COPY requirements.txt .
RUN pip install --index-url http://10.0.98.76:30004/repository/pip-proxy/simple --trusted-host 10.0.98.76 --default-timeout=100 --no-cache-dir -r requirements.txt
COPY . .
CMD ["/bin/bash"]
