# Service configuration

The service layer is set up with a YAML config file. Here's a simple example:

```yaml
services:
  example-service:
    # `info` will be exposed on the server status endpoint
    info: This is an example service

    # `host + health` will be used for health checks
    # `host + api` will be made available through Gateway
    host: http://example-service:6000
    health: /health
    api: /api

    # configuration for RPC endpoints provided by the service
    rpc:
      example_class:
        access:
          pre: /api/pre_access_obj_example_class
        create:
          pre: /api/pre_create_obj_example_class
          post: /api/post_create_obj_example_class
          diff:
            added_field:
              type: string
          meta:
            required_metadata:
              type: string
        update:
          pre: /api/pre_update_obj_example_class
          post: /api/post_update_obj_example_class
          diff:
            --removed_field:
              type: string
          meta:
            required_metadata:
              type: string
        delete:
          post: /api/post_delete_obj_example_class
        relations:
          related_class:
            create:
              pre: /api/pre_create_rel_example_class_related_class
            update:
              pre: /api/pre_update_rel_example_class_related_class

```

RPC hooks are configurable per domain class, and many combinations of `pre|post`, `access|create|update|delete`, for objects and their relations, with some exceptions. The following hooks are currently NOT implemented for various reasons; this may change in the future:

- `pre access relation` - `pre access object` will trigger for the related object type
- `pre delete object` - no sense in changing something before deletion
- `pre delete relation` - no sense in changing something before deletion
- `post access object` - no sense in changing something after it is read
- `post access relation` - no sense in changing something after it is read
- `pre create relation` - not implemented for GraphQL
- `pre update relation` - not implemented for GraphQL
- `post create relation` - not implemented for GraphQL
- `post update relation` - not implemented for GraphQL
- `post delete relation` - not implemented for GraphQL

HTTP paths for the RPC listeners are relative to `host`, but could otherwise be anything. In the configuration above, `http://example-service:6000/api/pre_create_obj_example_class` would be called with a JSON structure representing the `example` domain object every time such an object is created – giving an opportunity to modify the object before storing it. `post` RPC calls are called ASAP after the object is read or written, but won't delay the request-response cycle – giving an opportunity to react to changes in some way.

A template service configuration can be extracted from the docker image as a starting point:

```bash
docker run protojour/memoriam config --service > service_config.yml
```

The service config path can be set using `SERVICE_CONFIG_PATH` (used by domain nodes). Services can also be added using the service API.
