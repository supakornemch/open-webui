-- LiteLLM gets its own DB. It runs `prisma migrate deploy` at startup and will
-- DROP every table it doesn't own if pointed at a schema it didn't create.
SELECT 'CREATE DATABASE litellm' WHERE NOT EXISTS (
  SELECT FROM pg_database WHERE datname = 'litellm'
)\gexec
