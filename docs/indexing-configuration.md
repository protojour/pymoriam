# Indexing configuration

Indexes are an important tool for database performance, and adding indexes for fields used in filter and sort operations can speed up queries dramatically. In order to index fields, you need to supply a configuration that references your database schema. A very simple example is given below:

```yaml
collections:

  example_collection:
    example_field:
      # index parameters correspond to ArangoDB index parameters
      type: persistent      # type is required
      unique: true          # default is false
      sparse: true          # default is false
      deduplicate: false    # default is true
      inBackground: false   # default is true

edge_collections:

  example_relation:
    example_field:
      type: persistent
```

Special fields used by Memoriam, such as `_class` are indexed automatically, and do not need to be specified.

Detailed documentation on what index types are available and how they work can be found in the [ArangoDB documentation](https://www.arangodb.com/docs/stable/indexing.html).

A template index configuration can be extracted from the docker image as a starting point:

```bash
docker run protojour/memoriam config --index > index_config.yml
```

The index config can be set using `INDEX_CONFIG_PATH` (used by storage nodes).
