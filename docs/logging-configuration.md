# Logging configuration

Memoriam's logging configuration mirrors Python's [logging.config](https://docs.python.org/3/library/logging.config.html) in YAML, and can easily be changed to use e.g. `logging.FileHandler`. It is overridden by the following environment variables:

- `ERROR_LOG` (default: `True`)
- `ACCESS_LOG` (default: `False`)
- `AUDIT_LOG` (default: `False`)
- `AQL_LOG` (default: `False`)
- `PERF_LOG` (default: `False`)
- `LOG_LEVEL` (default: `DEBUG` in debug mode, otherwise `INFO`)

The default logging config is given below:

```yaml
version: 1

formatters:
  generic:
    datefmt: '%Y-%m-%d %H:%M:%S %z'
    format: '[%(asctime)s] [%(process)d] [%(levelname)s] %(message)s'

  access:
    datefmt: '%Y-%m-%d %H:%M:%S %z'
    format: '[%(asctime)s] [%(process)d] [%(levelname)s] %(host)s %(request)s %(status)d %(byte)d %(message)s'

handlers:
  console:
    class: logging.StreamHandler
    formatter: generic
    stream: sys.stdout

  console_error:
    class: logging.StreamHandler
    formatter: generic
    stream: sys.stderr

  console_access:
    class: logging.StreamHandler
    formatter: access
    stream: sys.stdout

loggers:
  memoriam:
    handlers:
      - console
    level: INFO

  memoriam.aql:
    handlers:
      - console
    level: INFO
    propagate: false

  memoriam.audit:
    handlers:
      - console
    level: INFO
    propagate: false

  memoriam.error:
    handlers:
      - console_error
    level: INFO
    propagate: false

  memoriam.perf:
    handlers:
      - console
    level: INFO
    propagate: false

  sanic.root:
    handlers:
      - console
    level: INFO

  sanic.error:
    handlers:
      - console_error
    level: INFO
    propagate: false

  sanic.access:
    handlers:
      - console_access
    level: INFO
    propagate: false

  sanic.server:
    handlers:
      - console
    level: INFO
    propagate: false
```

Memoriam's default logging configuration can be extracted from the docker image as a starting point:

```bash
docker run protojour/memoriam config --logging > logging_config.yml
```
