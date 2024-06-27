# Database schemas

Memoriam uses [JSON Schema](https://json-schema.org/)-based database schemas, in YAML format. Here's a very simple example:

```yaml
all: &all
  _id:
    type: string
    readOnly: true
  _key:
    type: string
    readOnly: true
  _rev:
    type: string
    readOnly: true

edges: &edges
  _from:
    type: string
  _to:
    type: string

collections:
  example_collection:
    type: object
    properties:
      <<: *all
      example_field:
        type: string
        readOnly: true

edge_collections:
  example_relation:
    type: object
    properties:
      <<: [*all, *edges]
    required:
      - _from
      - _to
```

Internal fields such as `_class` and `_index`, and collections used internally by Memoriam (domains, audit logging etc.) are handled automatically, and do not need to be part of your schema.

Low-level ArangoDB schema management and migrations may be handled with the command-line tool [Migrado](https://github.com/protojour/migrado). It is included in the Memoriam docker image:

```bash
docker run protojour/memoriam migrado
```

Detailed documentation on database schemas can be found in the [Migrado](https://github.com/protojour/migrado) README.

A template database schema can be extracted from the docker image as a starting point:

```bash
docker run protojour/memoriam config --db > db_schema.yml
```

The database schema path can be set using `ARANGO_SCHEMA_PATH` (used by both domain and storage nodes).
