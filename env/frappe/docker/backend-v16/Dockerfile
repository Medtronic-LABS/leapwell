# Backend image for Frappe v16 (requires-python = ">=3.14,<3.15", node >= 24).
# The public frappe/bench:latest image is pinned to Debian 12 bookworm's
# default Python (3.11) and Node 18 -- both too old for v16 -- so this
# replaces it with an explicit Python 3.14 base plus a current Node.

FROM python:3.14-bookworm

ARG NODE_MAJOR=24
# Same major version as the db service in docker-compose.yml: pg_dump (bench backup) refuses a newer server,
# and Debian 12 ships client 15.
ARG POSTGRES_MAJOR=16

RUN apt-get update && apt-get install -y --no-install-recommends \
        git curl ca-certificates wget gnupg sudo cron \
        build-essential pkg-config \
        default-libmysqlclient-dev \
        mariadb-client \
        redis-tools \
        libssl-dev \
        wkhtmltopdf \
        vim less \
    && install -d /usr/share/postgresql-common/pgdg \
    && curl -fsSL -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc \
        https://www.postgresql.org/media/keys/ACCC4CF8.asc \
    && echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" \
        > /etc/apt/sources.list.d/pgdg.list \
    && curl -fsSL https://deb.nodesource.com/setup_${NODE_MAJOR}.x | bash - \
    && apt-get install -y --no-install-recommends nodejs postgresql-client-${POSTGRES_MAJOR} \
    && npm install -g yarn \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -g 1000 frappe \
    && useradd -m -u 1000 -g 1000 -s /bin/bash frappe \
    && usermod -aG sudo frappe \
    && echo "frappe ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/frappe

# System-wide, not `pip install --user`: the compose file bind-mounts the bench workspace over /home/frappe,
# which would hide anything installed under the home directory.
RUN pip install --no-cache-dir frappe-bench

USER frappe
WORKDIR /home/frappe
ENV PATH="/home/frappe/.local/bin:${PATH}"

CMD ["sleep", "infinity"]
