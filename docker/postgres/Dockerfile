FROM pgvector/pgvector:pg16

# The SpineAgent schema (context_store, skill_registry, pending_approvals, action_log)
# runs automatically on first container start via docker-entrypoint-initdb.d.
# AdventureWorks data is loaded separately via scripts/load_adventureworks.sh
# after the container is running — see README for instructions.
COPY init-spine-schema.sql /docker-entrypoint-initdb.d/02-spine-schema.sql
