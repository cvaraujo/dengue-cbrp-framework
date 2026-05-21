FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends locales && \
    sed -i '/pt_BR.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen pt_BR.UTF-8 && \
    update-locale LANG=pt_BR.UTF-8

ENV LANG=pt_BR.UTF-8
ENV LANGUAGE=pt_BR:pt
ENV LC_ALL=pt_BR.UTF-8

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    unzip \
    wget \
    ca-certificates \
    vim \
    gnupg \
    lsb-release \
    && rm -rf /var/lib/apt/lists/*

# PostgreSQL 16 + PostGIS 3
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

ENV PGDATA=/var/lib/postgresql/data

RUN mkdir -p /var/lib/postgresql/data && \
    chown -R postgres:postgres /var/lib/postgresql && \
    chmod 700 /var/lib/postgresql/data

COPY container-simulation-only/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]

EXPOSE 5432
EXPOSE 6868

ENV POSTGRES_HOST=localhost
ENV POSTGRES_PORT=5432
ENV POSTGRES_DB=dengue-propagation
ENV POSTGRES_USER=postgres
ENV POSTGRES_PASSWORD=postgres

COPY . .
RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Extract only GAMA (no simheuristic/C++ optimizer needed)
COPY external-libs /external-libs
RUN mkdir -p /external-libs/gama && \
    for file in /external-libs/*; do \
    if [ -f "$file" ]; then \
    case "$(basename "$file")" in \
    GAMA_1.9.2_Linux_with_JDK.zip) \
    unzip -o "$file" -d /external-libs/gama ;; \
    *.tar.gz) \
    tar -xzf "$file" -C /external-libs/gama ;; \
    *.tar) \
    tar -xf "$file" -C /external-libs/gama ;; \
    esac \
    fi \
    done

RUN chmod -R 777 /external-libs/gama/headless

RUN sed -i 's/-Xms8192m/-Xms65536m/g' /external-libs/gama/Gama.ini && \
    sed -i 's/-Xmx8192m/-Xmx65536m/g' /external-libs/gama/Gama.ini && \
    sed -i 's/-Xmn2048m/-Xmn8192m/g' /external-libs/gama/Gama.ini && \
    sed -i 's/-Xms8192m/-Xms65536m/g' /external-libs/gama/headless/gama-headless.sh

CMD ["/bin/bash"]
#
# How to run:
#   ./container-simulation-only/run-docker.sh
#
# Or manually:
#   docker build -f container-simulation-only/Dockerfile -t dengue-simulation .
#   docker run --rm -it dengue-simulation bash -c 'python3 src/main.py <output_folder> <prev_date> <start_date>'
#
