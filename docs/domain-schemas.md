# Domain schemas

```{include} ../onto/SchemaGuide.md
```

A template domain schema can be extracted from the docker image as a starting point:

```bash
docker run protojour/memoriam config --db > db_schema.yml
```

The domain schema path can be set using `DOMAIN_SCHEMA_PATH` (used by domain nodes). Domains can also be added using the service API or through Onto.
