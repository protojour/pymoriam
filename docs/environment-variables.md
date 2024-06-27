# Environment variables

- `DEBUG`: Enables debug mode. Should not be used in production. (default: `False`)
- `NO_AUTH`: Disables authentication. Should not be used in production. (default: `False`)
- `NO_AC`: Disables access control. Should not be used in production. (default: `False`)
- `AUTO_RELOAD`: Auto-reload workers on code changes (default: `False`)
- `AUTO_TLS`: Auto-generate self-signed certificate for development. (default: `False`)
- `ERROR_LOG`: Enables error logging (default: `True`)
- `ACCESS_LOG`: Enables logging of HTTP requests (default: `False`)
- `AUDIT_LOG`: Enable audit logging; logs creation, updates and deletion of all domain objects with the `audit` trigger (default: `False`)
- `AUDIT_LOG_DB`: Enable audit logging to the database (default: `False`)
- `AUDIT_VERSIONING`: Enable audit versioning, updates audited domain objects with its current revision in the audit log (default: `False`)
- `AQL_LOG`: Enables logging of AQL queries (default: `False`)
- `PERF_LOG`: Enables logging of performance data (default: `False`)
- `LOG_LEVEL`: Override log level (default: `DEBUG` in debug mode, otherwise `INFO`)
- `CERT_FILE`: Path to a certificate file for the given service. `KEY_FILE` also needs to be set. Since Memoriam is designed to be exposed through the API Gateway, terminating TLS here might be sufficient.
- `KEY_FILE`: Path to a certificate key for the given service.
- `CA_FILE`: Path to a CA bundle for verifiying outgoing (cross-service) https requests. Uses system defaults if not set, may be set to an empty or falsey value to disable verification.
- `GATEWAY_HOST`: Hostname for connecting to the API Gateway (default: `memoriam-gateway`)
- `GATEWAY_PORT`: Port for connecting to the API Gateway (default: `5001`)
- `GATEWAY_TLS`: Enable TLS for the API Gateway. Requires `CERT_FILE` and `KEY_FILE` to be set. (default: `False`, but highly recommended)
- `DOMAIN_HOST`: Hostname for connecting to the Domain Service (default: `memoriam-domain`)
- `DOMAIN_PORT`: Port for connecting to the Domain Service (default: `5002`)
- `DOMAIN_TLS`: Enable TLS for the Domain Service. Requires `CERT_FILE` and `KEY_FILE` to be set. (default: `False`)
- `STORAGE_HOST`: Hostname for connecting to the Storage Service (default: `memoriam-storage`)
- `STORAGE_PORT`: Port for connecting to the Storage Service (default: `5003`)
- `STORAGE_TLS`: Enable TLS for the Storage Service. Requires `CERT_FILE` and `KEY_FILE` to be set. (default: `False`)
- `ARANGO_DB_NAME`: Name of the main Memoriam database (default: `memoriam`)
- `ARANGO_DOMAIN_DB_NAME`: Name of the domain metadata Memoriam database (default: `memoriam`)
- `ARANGO_CONNECT_RETRIES`: Number of retries when connecting to ArangoDB (default: `20`)
- `ARANGO_CONNECT_BACKOFF`: Time between retries when connecting to ArangoDB (default: `.5`)
- `ARANGO_SCHEMA_PATH`: Memoriam does not provide a backend database schema, but will import one if given the path (see [Database schemas](database-schemas.md))
- `DOMAIN_SCHEMA_PATH`: Memoriam does not provide a default domain, but will import one if given the path (see [Domain schemas](domain-schemas.md))
- `INDEX_CONFIG_PATH`: Path to indexing configuration for selected collections and fields (see [Indexing configuration](indexing-configuration.md)). 
- `SEARCH_CONFIG_PATH`: To use ArangoSearch features (such as `search` parameters in APIs), Memoriam needs a search config to match your backend database schema (see [Search configuration](search-configuration.md))
- `SERVICE_CONFIG_PATH`: To set up services, Memoriam needs a service config (see [Service configuration](service-configuration.md))
- `LOGGING_CONFIG_PATH`: To change logging behaviour, Memoriam needs a logging config (see [Logging configuration](logging-configuration.md)). 
- `AUTHLY_HOST`: Hostname for connecting to the Authly authentication service (default: `authly`)
- `AUTHLY_PORT`: Port for connecting to the Authly authentication service (default: `5004`)
- `REDIS_HOST`: Hostname for connecting to Redis (default: `redis`)
- `REDIS_PORT`: Port for connecting to Redis (default: `6379`)
- `REDIS_TLS`: Use TLS for connecting to Redis (default: `False`)
- `REDIS_DATABASE`: Redis database to use (default: `0`)
- `REDIS_PASSWORD`: Password for connecting to Redis (default: no authentication)
- `SENTRY_DSN`: Enables Sentry integration, given a valid DSN string
- `REQUEST_MAX_SIZE`: Max size of a request in bytes (default: `20000000000` (20 GB))
- `REQUEST_TIMEOUT`: Timeout waiting for a request to complete, in seconds (default: `60`)
- `RESPONSE_TIMEOUT`: Timeout for processing and returning a response, in seconds (default: `60`)
- `KEEPALIVE_TIMEOUT`: Timeout for keeping a TCP connection open when using the `Keep-Alive` header, in seconds (default: `10`)
- `WEBSOCKET_LOOP_TIMEOUT`: Iteration time for websocket reverse proxy (default: `1`)
- `WEBSOCKET_PING_INTERVAL`: Downstream (client) ping interval for websocket reverse proxy (default: `20`)
- `WEBSOCKET_PING_TIMEOUT`: Downstream (client) ping timeout for websocket reverse proxy (default: `5`)
- `BACKLOG`: Number of unaccepted connections allowed before refusing new connections (default: `100`)

## Gateway-specific environment variables:

- `GATEWAY_WORKERS`: Number of workers for the API Gateway (default: `1`). Additional workers requires Redis, see notes on [scaling](environment-variables.md#scaling).
- `HOST_DOCS`: Serve the Memoriam documentation. Likely unwanted in production. (default: `False`)
- `COMPRESS_LEVEL`: Brotli/Gzip compression level (1-9, default: `6`)
- `COMPRESS_MIN_SIZE`: Minimum number of bytes for compression (default: `256`)
- `CORS`: Whether to enable CORS protection (default: `True`)
- `CORS_ALLOW_HEADERS`: Value of the header `access-control-allow-headers` (default: `*`)
- `CORS_ALWAYS_SEND`: Whether to always send the header `access-control-allow-origin` (default: `True`)
- `CORS_AUTOMATIC_OPTIONS`: Whether to automatically generate `OPTIONS` endpoints for routes that do not have one defined (default: `True`)
- `CORS_EXPOSE_HEADERS`: Value of the header `access-control-expose-headers` (default: `''`)
- `CORS_MAX_AGE`: Value of the header `access-control-max-age` (default: `0`)
- `CORS_METHODS`: Value of the header `access-control-access-control-allow-methods` (default: `''`)
- `CORS_ORIGINS`: Value of the header `access-control-allow-origin` (default: `*`)
- `CORS_SEND_WILDCARD`: Whether to send a wildcard origin instead of the incoming request origin (default: `False`)
- `CORS_SUPPORTS_CREDENTIALS`: Value of the header `access-control-allow-credentials` (default: `False`)
- `CORS_VARY_HEADER`: Whether to add the `vary` header (default: `True`)

## Domain-specific configuration variables:

- `DOMAIN_WORKERS`: Number of workers for the Domain Service (default: `1`). Additional workers requires Redis, see notes on [scaling](environment-variables.md#scaling).
- `RELOAD_SCHEMAS`: Auto-reload workers on schema changes (default: `False`)
- `NO_DELETE`: Disallows deletion. Delete endpoints are not removed, but return `405 Method not allowed`. Should be enforced using access control, however, this option is provided for simple use cases (default: `False`)
- `ARANGO_DEFAULT_LIMIT`: The default number of results to return from APIs, if not otherwise specified (default: `100`)

## Storage-specific configuration variables:

- `STORAGE_WORKERS`: Number of workers for the Storage Service (default: `1`). Additional workers requires Redis, see notes on [scaling](environment-variables.md#scaling).
- `INIT_DB`: Controls whether Memoriam tries to initialize databases, collections and indexes on server start (default: `True`)
- `INIT_SEARCH`: Controls whether Memoriam tries to initialize search views and analyzers on server start (default: `True`)
- `UPDATE_SEARCH`: Triggers an update of all `_index` fields that are unpopulated or outdated on server start (**warning:** may run for a long time; default: `False`)
- `ARANGO_HOST`: Hostname for connecting to ArangoDB (default: `arangodb`)
- `ARANGO_PORT`: Port for connecting to ArangoDB (default: `8529`)
- `ARANGO_TLS`: Use TLS when connecting to ArangoDB (default: `False`)
- `ARANGO_HOSTS`: List of comma-separated hostnames for connecting (round-robin) to an ArangoDB cluster (e.g. `http://coordinator1:8529,http://coordinator2:8529,http://coordinator3:8529`). If specified, `ARANGO_HOST`, `ARANGO_PORT` and `ARANGO_TLS` are ignored.
- `ARANGO_ROOT_USERNAME`: Username for root-level access to ArangoDB (default: no authentication)
- `ARANGO_ROOT_PASSWORD`: Password for root-level access to ArangoDB (default: no authentication)
- `ARANGO_USERNAME`: Username for user-level access to ArangoDB (default: no authentication)
- `ARANGO_PASSWORD`: Password for user-level access to ArangoDB (default: no authentication)
- `MINIO_HOST`: Hostname for connecting to Minio (default: `minio`)
- `MINIO_PORT`: Port for connecting to Minio (default: `9000`)
- `MINIO_TLS`: Use TLS for connecting to Minio (default: `False`)
- `MINIO_ROOT_USER`: Access key for connecting to Minio. The storage service and Minio should have the same variable set.
- `MINIO_ROOT_PASSWORD`: Access key for connecting to Minio. The storage service and Minio should have the same variable set.
- `MINIO_MAX_FILESIZE`: Maximum filesize in bytes allowed for upload to Minio (default: `26214400`)

## Scaling

Increasing the number of workers enables each instance to handle more connections. We recommend setting `GATEWAY_WORKERS`, `DOMAIN_WORKERS` and `STORAGE_WORKERS` to the number of processors available on each server instance, respectively. Horizontal scaling can be acheived by increasing the number of instances per mode; the Domain service in particular will usually have higher workloads.
