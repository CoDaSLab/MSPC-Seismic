FROM ubuntu:latest

RUN apt-get update && \
    apt-get install -y python3 python3-pip python3-venv && \
    apt-get install -y nano && \
    apt-get install -y sudo && \
    apt-get clean

# Crear un entorno virtual y activar
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Instalar dependencias de Python en el entorno virtual
COPY requirements.txt requirements.txt
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

RUN useradd -u 1013 -s /bin/bash vulcano 
USER vulcano

WORKDIR /home/vulcano

CMD ["bash"]