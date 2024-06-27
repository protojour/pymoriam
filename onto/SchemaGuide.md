A domain schema is a YAML-based document that describes the Domain in detail through its classes, their attributes and relations, and how they interact with your data model.

The basic structure of a Domain is a YAML map, with class names as keys. Each class has the following structure:

```yaml
Domain Class Name:
  description: Domain class description text  # required
  resolver: collection_name                   # required
  permissive: output                          # input, output or both, default: no
  operations:                                 # default (all)
    - read
  constants:
    constant_name: value
  attributes:
    attribute_name: resolver_attribute_name
  relations:
    relation_name_a: [Other Class, edge_collection, inbound]
    relation_name_b: [[Other Class, Another Class], edge_collection, outbound]
    relation_name_c: [ANY, edge_collection, 1..2 outbound]
    relation_name_d: [[ANY], edge_collection, any]
  triggers:
    - audit
```

Class name (here, `Domain Class Name`) must be unique within the Domain, but keep in mind it will be used to address domain data in APIs. Case conversion will be used, so "unique" here means unique, case- and space-insensitive. Alphanumeric characters, spaces, dashes and underscores may be used.

`description` (no default, **required**) is used for documenting Domains and their APIs.

`resolver` (no default, **required**) refers to an existing backend database collection, which will be used to store the data for a given domain class.

`class` (default: class name, snake_cased) overrides the actual `_class` attribute used for this class in when storing and retrieving data. This allows you to have classes referencing other classes in the domain, or even in another domain. This does not affect RPC triggers. `class` should be snake_cased, mirroring how `_class` is written by Memoriam, but is purposefully kept flexible.

`alias` (default: None) is used if this class is an alias for another class defined in the same domain. Outward, they will appear to be the same class, using the value of `alias` for names, paths, etc. However, this allows you to use a different set of attributes and other properties for each set of operations:

```yaml
Alias Class:
  # ...
  alias: Domain Class Name
  operations:
    - create
  attributes:
    required_attribute_name: resolver_attribute
```

`permissive` (default: `no`) is a string value, and can either be `input`, `output` or `both`. Setting permissive to one of these allows additional attributes not covered by the schema to be passed along on input, output, or both, respectively. By default, all additional attributes are discarded.

`operations` (default: all) is a list of valid operations on objects of this domain class; valid list values are `create`, `read`, `update` and `delete` ("CRUD"). Omitting `operations` will allow all operations.

`constants` (default: None) is a map of attributes with constant values, added to data on output. Values can be any string, numeric or boolean value.

`attributes` (default: None) is a map of domain class attribute names to `resolver` collection attribute names.

`relations` (default: None) is a map of relations (graph edges) to other domain classes. Values are lists with three values; _edge spec_, _edge resolver_, and _[depth] direction_.

The _edge spec_ may be a single domain class name (string) or multiple domain class names (list of strings). The string form indicates this class may have only one relation to the given class, while the list form indicates this class may have multiple relations to given class(es). In list form, a single member indicates multiple relations to a single given class. Referring to the current class is allowed. In addition, the special value `ANY` will allow relations to any domain class.

The _edge resolver_ must refer to an existing backend database edge collection, which will be used to resolve the relations.

_[depth] direction_ is a string where the first part (_depth_) is optional. _direction_ may have one of three values, `outbound` (domain class is source of relation), `inbound` (domain class is target of relation) or `any` (domain class can be either).

_depth_ refers to the number of edges that must be traversed to find domain classes in the edge spec. Valid values are `1` (default), `2`, `1..2`, `2..4` and so on, or more generally, `min[..max]`. If _depth_ is used, it is separated from `direction` with a single space.

`triggers` (default: None) is a list of trigger functions for common operations in Memoriam, to be called when an object of this class is stored through the GraphQL og REST APIs.

The following trigger values are available:

- `set_creator`: objects are tagged with a unique user id from the auth service
- `set_created`: objects are timestamped with a ISO-8601 datetime on creation
- `set_updated`: objects are timestamped with a ISO-8601 datetime on every update
- `audit`: all changes to objects and their closest relations are logged
