FROM python:3.10-slim-bookworm AS base

WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# Configure Tsinghua mirror for Debian
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's/security.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources

FROM base AS build

# Update package list and install build dependencies and LibreOffice
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libreoffice && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Build Python dependencies
#COPY requirements.txt .
#RUN python -m venv /app/venv && \
#    . /app/venv/bin/activate && \
#    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple && \
#    pip uninstall -y paddlepaddle && \
#    pip install -i https://www.paddlepaddle.org.cn/packages/stable/cu123/ \
#        paddlepaddle-gpu==3.0.0b2 && \
#    pip install PyMuPDF tqdm paddleocr python-docx -i https://pypi.tuna.tsinghua.edu.cn/simple

# Build Python dependencies
COPY requirements.txt .
RUN python -m venv /app/venv && \
    . /app/venv/bin/activate && \
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip uninstall -y torch torchvision torchaudio && \
    pip install torch==2.4.1 torchvision torchaudio \
        -f https://download.pytorch.org/whl/torch_stable.html && \
    pip uninstall -y paddlepaddle && \
    pip install -i https://www.paddlepaddle.org.cn/packages/stable/cu123/ \
        paddlepaddle-gpu==3.0.0b2 && \
    pip install PyMuPDF tqdm paddleocr python-docx -i https://pypi.tuna.tsinghua.edu.cn/simple



# Download models
COPY hf-cache/ /opt/
COPY download_models.py .
RUN . /app/venv/bin/activate && \
    python download_models.py

FROM base AS prod

# Copy Python dependencies and models from the build stage
COPY --from=build /app/venv /app/venv
COPY --from=build /opt/models /opt/models
COPY --from=build /opt/layoutreader /opt/layoutreader

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libgomp1 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create volume for paddleocr models
RUN mkdir -p /root/.paddleocr
VOLUME [ "/root/.paddleocr" ]

# Copy the app and its configuration file
COPY entrypoint.sh /app/entrypoint.sh
COPY magic-pdf.json /root/magic-pdf.json
COPY app.py /app/app.py

# Expose the port that FastAPI will run on
EXPOSE 8000

# use root to run app
USER root

# Command to run FastAPI using Uvicorn
ENTRYPOINT [ "/app/entrypoint.sh" ]
CMD ["--host", "0.0.0.0", "--port", "8000"]
