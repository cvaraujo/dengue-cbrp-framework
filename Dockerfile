FROM --platform=linux/amd64 python:3.12-slim AS python-base

# Set work directory
WORKDIR /app

# Set locale to pt_BR.UTF-8 for PostgreSQL installation and runtime
RUN apt-get update && \
    apt-get install -y --no-install-recommends locales && \
    sed -i '/pt_BR.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen pt_BR.UTF-8 && \
    update-locale LANG=pt_BR.UTF-8

ENV LANG=pt_BR.UTF-8
ENV LANGUAGE=pt_BR:pt
ENV LC_ALL=pt_BR.UTF-8

# Install system dependencies for Python and C++
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    g++ \
    unzip \
    wget \
    ca-certificates \
    libpqxx-dev \
    libzmq3-dev \
    vim \
    gnupg \
    lsb-release \
    && rm -rf /var/lib/apt/lists/*

# Install cppzmq (header-only library)
# Instalar cppzmq (headers-only)
RUN wget https://raw.githubusercontent.com/zeromq/cppzmq/master/zmq.hpp -O /usr/include/zmq.hpp

# Add PostgreSQL 16 APT repository and install PostgreSQL 16 and PostGIS 3
RUN apt-get update && \
    mkdir -p /etc/apt/keyrings && \
    wget --quiet -O /etc/apt/keyrings/pgdg.asc https://www.postgresql.org/media/keys/ACCC4CF8.asc && \
    echo "deb [signed-by=/etc/apt/keyrings/pgdg.asc] http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    postgresql-16 \
    postgresql-client-16 \
    postgis \
    postgresql-16-postgis-3 \
    postgresql-16-postgis-3-scripts \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables for PostgreSQL
ENV PGDATA=/var/lib/postgresql/data

# Create PostgreSQL data directory with correct permissions
RUN mkdir -p /var/lib/postgresql/data && \
    chown -R postgres:postgres /var/lib/postgresql && \
    chmod 700 /var/lib/postgresql/data

# Set up entrypoint to start both PostgreSQL and your app
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]

# Expose ports for TCP connections (e.g., for your Python app and PostgreSQL if needed)
EXPOSE 2021
EXPOSE 5432
EXPOSE 6868

# (Optional) Set environment variables for PostgreSQL connection
ENV POSTGRES_HOST=localhost
ENV POSTGRES_PORT=5432
ENV POSTGRES_DB=dengue-propagation
ENV POSTGRES_USER=postgres
ENV POSTGRES_PASSWORD=postgres

# Copy requirements.txt and install Python dependencies
COPY . .
RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy and extract external libraries
COPY external-libs /external-libs
RUN mkdir -p /external-libs/gama && \
    mkdir -p /external-libs/simheuristic && \
    for file in /external-libs/*; do \
    if [ -f "$file" ]; then \
    case "$(basename "$file")" in \
    GAMA_1.9.2_Linux_with_JDK.zip) \
    unzip -o "$file" -d /external-libs/gama ;; \
    *.zip) \
    unzip -o "$file" -d /external-libs/simheuristic ;; \
    *.tar.gz) \
    tar -xzf "$file" -C /external-libs/gama ;; \
    *.tar) \
    tar -xf "$file" -C /external-libs/gama ;; \
    esac \
    fi \
    done

RUN chmod -R 777 /external-libs/gama/headless

# Increase GAMA JVM memory to 16GB for large experiments
RUN sed -i 's/-Xms8192m/-Xms12288m/g' /external-libs/gama/Gama.ini && \
    sed -i 's/-Xmx8192m/-Xmx12288m/g' /external-libs/gama/Gama.ini && \
    sed -i 's/-Xmn2048m/-Xmn8192m/g' /external-libs/gama/Gama.ini && \
    sed -i 's/-Xms8192m/-Xms12288m/g' /external-libs/gama/headless/gama-headless.sh

# Optional local archives: docker-build-deps/ is included by COPY . . above.
# Single RUN reads /app/docker-build-deps directly (avoids stale layer cache where /tmp had only Boost).
RUN mkdir -p /opt && \
    DEPS=/app/docker-build-deps && \
    if [ -d "$DEPS" ]; then echo "[docker] docker-build-deps:"; ls -la "$DEPS" || true; fi && \
    if [ -f "$DEPS/boost_1_90_0.tar.gz" ]; then \
    echo "[docker] Using local $DEPS/boost_1_90_0.tar.gz"; \
    tar -xzf "$DEPS/boost_1_90_0.tar.gz" -C /opt; \
    else \
    echo "[docker] Downloading Boost 1.90.0..."; \
    wget -q https://archives.boost.io/release/1.90.0/source/boost_1_90_0.tar.gz -O /tmp/boost_1_90_0.tar.gz && \
    tar -xzf /tmp/boost_1_90_0.tar.gz -C /opt && \
    rm -f /tmp/boost_1_90_0.tar.gz; \
    fi && \
    if [ -f "$DEPS/lemon-1.3.1.zip" ]; then \
    echo "[docker] Using local $DEPS/lemon-1.3.1.zip"; \
    unzip -q "$DEPS/lemon-1.3.1.zip" -d /opt; \
    elif [ -f "$DEPS/lemon-1.3.1.tar.gz" ]; then \
    echo "[docker] Using local $DEPS/lemon-1.3.1.tar.gz"; \
    tar -xzf "$DEPS/lemon-1.3.1.tar.gz" -C /opt; \
    else \
    echo "[docker] Downloading LEMON 1.3.1..."; \
    wget -q http://lemon.cs.elte.hu/pub/sources/lemon-1.3.1.zip -O /tmp/lemon-1.3.1.zip && \
    unzip -q /tmp/lemon-1.3.1.zip -d /opt && \
    rm -f /tmp/lemon-1.3.1.zip; \
    fi

# Build and install LEMON from source
WORKDIR /opt/lemon-1.3.1
RUN cmake . && \
    make -j
WORKDIR /app

# Pre-compile cbrp-simheur so it's ready at runtime (make will be a no-op if unchanged)
WORKDIR /external-libs/simheuristic/cbrp-simheuristic
RUN cmake . && \
    make cbrp-simheur -j
WORKDIR /app

# Set up a base for C++ builds with CMake
FROM python-base AS cpp-base

# Set environment variables for C++ builds
ENV CC=gcc
ENV CXX=g++

# Default command (can be overridden)
CMD ["/bin/bash"]
# 
# How to run this Dockerfile:
#
# 1. Build the Docker image (from the directory containing this Dockerfile):
#    docker build -t my-app .
#
# 2. Run a container from the built image:
#    docker run --rm -it my-app
#
#    (You can override the default command by appending your own, e.g.
#     docker run --rm -it my-app python src/main.py)
# 
# 3. To mount your source code or data, use the -v option:
#    docker run --rm -it -v $(pwd):/app my-app
