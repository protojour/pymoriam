# Search configuration

To use text search features, you need to supply a configuration that references your database schema. Memoriam collects searchable data from configured collections and fields, into a field called `_index`. A very simple example is given below:

```yaml
view_name: memoriam_text_search

default_collection_props: &default
  fields:
    _index:
      analyzers:
        - text_en

# Searchable collections are linked here, with *default being the config above:
view_props:
  links:
    example_collection: *default

# Fields collected into _index from each collection are configured here:
index_fields:
  example_collection:
    - example_field
```

A template search configuration can be extracted from the docker image as a starting point:

```bash
docker run protojour/memoriam config --search > search_config.yml
```

The search config path can be set using `SEARCH_CONFIG_PATH` (used by both domain and storage nodes).
