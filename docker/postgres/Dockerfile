FROM pgvector/pgvector:pg16

# Install build dependencies for AdventureWorks loader
RUN apt-get update && apt-get install -y \
    git \
    ruby \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Clone AdventureWorks-for-Postgres
WORKDIR /tmp/adventureworks
RUN git clone https://github.com/lorint/AdventureWorks-for-Postgres.git .

# Download and extract the AdventureWorks OLTP CSV data
RUN wget -q "https://github.com/Microsoft/sql-server-samples/releases/download/adventureworks/AdventureWorks-oltp-install-script.zip" -O aw.zip \
    && unzip -o aw.zip -d . \
    && rm aw.zip

# Convert CSVs from Windows format to Postgres-compatible format
RUN ruby update_csvs.rb

# Copy the install script into the Docker entrypoint init directory
# so it runs automatically on first container start
RUN cp install.sql /docker-entrypoint-initdb.d/01-adventureworks.sql

# Copy CSV data to a location accessible by the install script
RUN cp *.csv /tmp/adventureworks/

# The install.sql references CSV paths relative to the working directory.
# We patch it to use absolute paths so it works from the entrypoint.
RUN sed -i "s|\\\\copy|\\\\copy|g" /docker-entrypoint-initdb.d/01-adventureworks.sql

# Copy the additional schema for SpineAgent tables
COPY init-spine-schema.sql /docker-entrypoint-initdb.d/02-spine-schema.sql

# Set working directory so \copy in install.sql finds the CSVs
WORKDIR /tmp/adventureworks

# pgvector extension will be created via the schema init script
