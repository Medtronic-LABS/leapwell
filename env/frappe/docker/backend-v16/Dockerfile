# Backend image for Frappe v16 (requires-python = ">=3.14,<3.15", node >= 24).
# The public frappe/bench:latest image is pinned to Debian 12 bookworm's
# default Python (3.11) and Node 18 -- both too old for v16 -- so this
# replaces it with an explicit Python 3.14 base plus a current Node.

FROM python:3.14-bookworm

ARG NODE_MAJOR=24

RUN apt-get update && apt-get install -y --no-install-recommends \
        git curl ca-certificates wget gnupg sudo cron \
        build-essential pkg-config \
        default-libmysqlclient-dev \
        mariadb-client \
        postgresql-client \
        redis-tools \
        libssl-dev \
        wkhtmltopdf \
        vim less \
    && curl -fsSL https://deb.nodesource.com/setup_${NODE_MAJOR}.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g yarn \
    && rm -rf /var/lib/apt/lists/*

# Install bench system-wide: docker-compose.yml bind-mounts development/workspace over /home/frappe, which would
# hide a `pip install --user` under /home/frappe/.local.
RUN pip install --no-cache-dir frappe-bench

RUN groupadd -g 1000 frappe \
    && useradd -m -u 1000 -g 1000 -s /bin/bash frappe \
    && usermod -aG sudo frappe \
    && echo "frappe ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/frappe

USER frappe
WORKDIR /home/frappe
ENV PATH="/home/frappe/.local/bin:${PATH}"

CMD ["sleep", "infinity"]
