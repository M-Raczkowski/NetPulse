FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends iproute2 iperf3 && rm -rf /var/lib/apt/lists/*
COPY requirements/agent.txt requirements/agent.txt
RUN pip install --no-cache-dir -r requirements/agent.txt
COPY agent ./agent
COPY responder ./responder
CMD ["python", "-m", "agent.main"]