FROM pgvector/pgvector:pg16

# Install build dependencies
RUN apt-get update && apt-get install -y \
    git \
    python3 \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Clone AdventureWorks-for-Postgres (provides install.sql)
WORKDIR /tmp/adventureworks
RUN git clone https://github.com/lorint/AdventureWorks-for-Postgres.git .

# Download Microsoft AdventureWorks OLTP CSVs.
# Extract to a temp dir then flatten all CSVs into WORKDIR.
RUN wget -q "https://github.com/Microsoft/sql-server-samples/releases/download/adventureworks/AdventureWorks-oltp-install-script.zip" -O /tmp/aw.zip \
    && unzip -o /tmp/aw.zip -d /tmp/aw_extract \
    && find /tmp/aw_extract -name "*.csv" -exec cp {} /tmp/adventureworks/ \; \
    && rm -rf /tmp/aw.zip /tmp/aw_extract

# Convert CSVs from Microsoft +| format to tab-separated with proper quoting.
# Python csv.writer handles fields containing " or \t correctly (RFC 4180).
COPY convert_csvs.py /tmp/convert_csvs.py
RUN python3 /tmp/convert_csvs.py

# Verify conversion: first line of BusinessEntity.csv must contain a tab
RUN python3 -c "f=open('BusinessEntity.csv');l=f.readline();f.close();assert '\t' in l,'Conversion failed: '+repr(l[:100]);print('CSV OK:',repr(l[:60]))"

# Copy the install script into the Docker entrypoint init directory
RUN cp install.sql /docker-entrypoint-initdb.d/01-adventureworks.sql

# Copy the SpineAgent schema (context_store, skill_registry, pending_approvals, action_log)
COPY init-spine-schema.sql /docker-entrypoint-initdb.d/02-spine-schema.sql

# Keep WORKDIR so \copy in install.sql resolves CSV paths relative to here
