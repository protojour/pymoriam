# Authly operations scripts

For authorization and access control to work, Authly needs to be properly configured, and the easiest way to do this is with a YAML operations script. The script needs to be supplied to Authly's config directory, and set up using the `startup_file` configuration key.

A template operations script can be extracted from the docker image as a starting point:

```bash
docker run protojour/memoriam config --authly > authly_operations.yml
```

The template operations script that Memoriam outputs is shown below, and gives a general idea of how it's used, and what's possible. As you can see, Memoriam also uses this for core functionality. There are some parts of the reference configuration that shouldn't be changed, and some rules to follow:

```yaml
# root user
# owns the main service and should generally not be used
- set user:
    root:
      firstName: ""
      lastName: ""
      password: secret
      email: root@example.com

# main service
# should be named accordingly, change all occurences of name below
- set service:
    memoriam:
      serviceSecret: secret
      name: Memoriam
      host: memoriam.example.com
      domain: example.com
      ownerUsername: root

    onto:
      serviceSecret: secret
      name: Onto
      host: memoriam.example.com
      domain: example.com
      ownerServiceName: memoriam

# common users
# repeat for each common user, or use LDAP import
- set user:
    user:
      firstName: ""
      lastName: ""
      password: secret
      email: user@example.com
      name: ""

# services
# repeat for each service that interacts with main service
- set service:
    example_service:
      serviceSecret: secret
      name: Example Service
      host: example-service.example.com
      domain: example.com
      ownerServiceName: memoriam

# clients
# repeat for each client that _users_ interact with main service through
- set service:
    example_client:
      serviceSecret: secret
      name: Example Client
      host: example-client.example.com
      domain: example.com
      ownerServiceName: memoriam

# contracts
# set all relevant services to have a contract with main service
- set contract:
    memoriam:
      serviceNames:
        - onto
        - example_client
        - example_service

# groups
# repeat for each group of entities, or use LDAP import
- set group:
    users:
      usernames:
        - root
        - user

# roles
# repeat at least for each client, add users or groups
- set role:
    memoriam:
      onto_admin:
        usernames:
          - root

      onto_user:
        groupNames:
          - users

      example_client_user:
        groupNames:
          - users

# system api
# change or add policies, but don't change resources or action names
- set resource:
    memoriam:
      domain:
        create:
          Allow for Onto admins: >
            "onto_admin" in Profile.ServiceRoles
          Allow for services: >
            Profile.EntityType == "Service"
        read:
          Allow for all Onto users: >
            "onto_admin" in Profile.ServiceRoles ||
            "onto_user" in Profile.ServiceRoles
          Allow for services: >
            Profile.EntityType == "Service"
        update:
          Allow for Onto admins: >
            "onto_admin" in Profile.ServiceRoles
          Allow for services: >
            Profile.EntityType == "Service"
        delete:
          Allow for Onto admins: >
            "onto_admin" in Profile.ServiceRoles
          Allow for services: >
            Profile.EntityType == "Service"

      service:
        register:
          Allow for services: >
            Profile.EntityType == "Service"
        status:
          Allow for services: >
            Profile.EntityType == "Service"
        unregister:
          Allow for services: >
            Profile.EntityType == "Service"
        proxy:
          Allow for everyone: >
            true

      audit:
        create:
          Allow for services: >
            Profile.EntityType == "Service"
        read:
          Allow for services: >
            Profile.EntityType == "Service"

      storage:
        read_buckets:
          Allow for services: >
            Profile.EntityType == "Service"
        create_bucket:
          Allow for services: >
            Profile.EntityType == "Service"
        read_bucket:
          Allow for services: >
            Profile.EntityType == "Service"
        create_object:
          Allow for services: >
            Profile.EntityType == "Service"
        read_object:
          Allow for services: >
            Profile.EntityType == "Service"

# domain apis
# set up a resource for each exposed domain_class
# add policies as you see fit, but don't change action names
- set resource:
    memoriam:
      example_resource:
        create:
          Allow for all Example Client users: >
            "example_client_user" in Profile.ServiceRoles
          Allow for services: >
            Profile.EntityType == "Service"
        read:
          Allow for all Example Client users: >
            "example_client_user" in Profile.ServiceRoles
          Allow for services: >
            Profile.EntityType == "Service"
        update:
          Allow for all Example Client users: >
            "example_client_user" in Profile.ServiceRoles
          Allow for services: >
            Profile.EntityType == "Service"
        delete:
          Deny for everyone: >
            false
```

First of all, your main service should be described, its name is given here as `memoriam`. You should rename this to whatever your main service is called. Make sure to rename all references to `memoriam`, as this name (its `serviceName`) is used as a reference throughout.

Onto is Memoriam's built-in frontend client. It is set up as a service, but acts as a client towards Memoriam. It mainly accesses the `domain` resource. When acting as a client, it is the user's credentials that are used for authentication.

All other services are part of the service mesh, and should have a service contract with your main service, as Memoriam needs to know about the services that interact with it directly for them to be allowed to do so. Services have a `serviceName` and a `serviceSecret` used for authentication, corresponding to `username` and `password` for users.

For more finely-grained permissions that don't use `username` or `serviceName` directly, you should set up roles. Roles are groups of entities (users, groups, or even services) associated with a particular service, and gives policies something general to act on.

All the details on what is allowed or not is controlled through resources, which have any number of actions defined, and any number of policies for each action. The default result of each action is always `DENY`.

Memoriam has four resources defined, `domain`, `service`, `audit` and `storage`, corresponding to resources available in the System API. The names of these resources should not be changed. Furthermore, each resource has a set of actions, such as `create`, `read`, `update` and `delete`. For Memoriam, these should also be left as-is.

A resource should be created for each domain class exposed through generated domain APIs, and the actions associated with these are always `create`, `read`, `update` and `delete`. However, the policies are up to you.

Policies have a name (`Allow for services`), and an [Expr](https://github.com/expr-lang/expr) expression that should evaluate to `true` for `ALLOW` and `false` for `DENY`.

A number of different values are available in the environment exposed to Authly, `requestIP`, `username` and `serviceName`, values associated with the resource, the request, or time utilities. See the [Authly](https://software.situ.net/authly/docs/) documentation.


## LDAP setup

Authly offers LDAP integration and -synchronization. For authorities other than Authly, you will need to set these authorities enabled,
specify their sources (generic term for servers), and finally run synchronization. An example LDAP setup is shown below.

```yaml
- set authority:
    LDAP:
      enabled: true

- create source:
    LDAP:
      forumsys:
        enabled: true
        hostname: ldap.forumsys.com
        port: "389"
        tlsPort: "636"
        tlsEnabled: false
        readOnlyDN: cn=read-only-admin,dc=example,dc=com
        readOnlyPass: password
        baseDN: dc=example,dc=com
        bindDNTemplate: uid={uid},dc=example,dc=com
        userSyncFilter: (&(objectClass=inetOrgPerson))
        userTemplate:
          username: "{uid}"
          firstName: "{cn}"
          lastName: "{sn}"
          email: "{mail}"
        authParams:
          - name: uid
            description: User ID
            alias: User ID
            required: true

- run sync:
    LDAP:
      sourceNames:
        - forumsys
```

Most of these settings should be somewhat familiar to LDAP admins. The `userTemplate` specifies how LDAP users are synchronized to Authly users, and the `userSyncFilter` can be used to filter what entities should be synchronized. The `bindDNTemplate` specifies how to use user data in connection parameters.
