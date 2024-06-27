![Memoriam](docs/_static/memoriam.png)

> [!IMPORTANT]
> We are developing a [new version of Memoriam](https://software.situ.net/memoriam/docs/). This early version is in sunsetting mode until the end of 2024, and will not see any major feature development.

Memoriam is a software platform that takes care of much of the scaffolding needed in modern backend systems. We've combined Free and Open Source Software components with a highly configurable modular low-code approach, so that you can get a complete backend service up and running in no time.

Memoriam automatically generates detailed and secure REST and GraphQL APIs, and serves as a structured hub for your data domains, through which data is documented, verified and served. It can serve as a gateway for your services, allowing them to leverage these features, or extend the base functionality of the system.


## Running Memoriam

Memoriam relies on a small set of components, and the recommended way of running it is with Docker or Kubernetes. See the [Quickstart](docs/quickstart.md) and [Configuration](docs/configuration.md) documentation to get started.

Memoriam itself has a layered architecture, and needs three instances, running in three different modes:

- **Gateway mode**, which serves as the external entrypoint. The Gateway handles authentication and reverse proxy requests to the Domain and Storage layers.
- **Domain mode**, which serves the core Memoriam System API and generated REST or GraphQL APIs for configured domains. It also manages services.
- **Storage mode**, which provides isolated access to database and object storage APIs. Access control to data is enforced at this level.

Memoriam usually requires the following additional services:

- An [Authly](https://software.situ.net/authly/docs/) server for identity and access manangement
- An [ArangoDB](https://www.arangodb.com/) database, single instance or cluster.
- A Redis-compatible key-value store for for caching and worker synchronization, e.g. [ValKey](https://valkey.io/). Authly also uses Redis.
- An S3-compatible service for object storage, e.g. [MinIO](https://min.io/)

REST and GraphQL APIs have extensive documentation (OpenAPI specs and GraphQL schemas) to help you get started.


## Onto

![Onto](docs/_static/onto-screenshot.png)

Onto is a web client to manage and document the information model for Memoriam, and manage services in the Memoriam service mesh. It allows building an ontology from conceptual maps of your data domains, how they relate to other domains, and how they are represented in the database.


## Database

[ArangoDB](https://www.arangodb.com/docs/stable/) provides Memoriam with a performant and modern multi-model database layer using Document and Graph database paradigms. ArangoDB is run as a separate service, and may be sharded and clustered independently for each Storage node, according to your needs.

Low-level ArangoDB schema management and migrations may be handled with the command-line tool [Migrado](https://github.com/protojour/migrado)

> [!WARNING]
> ArangoDB is [no longer free and open source software](https://arangodb.com/2023/10/evolving-arangodbs-licensing-model-for-a-sustainable-future/).
>
> The last version of ArangoDB with a FOSS license is v3.11.


## Object storage

Object storage is provided by any S3 API-compatible storage service, we use [MinIO](https://docs.min.io/). Some of MinIO's relevant or notable features are encryption at transport and rest, bucket versioning, access and data retention policies. Objects are mirrored in the database layer through metadata objects, which allow them to be connected to the data graph and subject to additional fine-grained access control.


## Authentication and Access control

Authentication and access control is provided by [Authly](https://software.situ.net/authly/docs/).

As a bare minimum for authentication, Authly needs to be configured with a main Service (e.g. "memoriam"), and a set of users or services,

While Memoriam has basic CRUD limitations configrable through domain classes, Authly access control is much more flexible, allowing detailed policy rules per service, group, user, and more.

Please refer to the documentation on the [Authly documentation](https://software.situ.net/authly/docs/) for a complete overview.


## Development setup

You need recent versions of Python, Poetry, Docker and docker-compose installed locally.

Install dependencies:

```bash
poetry install
```

Run a simple dev environment with:

```bash
docker-compose up --build
```

Run test environment with:

```bash
docker-compose -f tests/docker-compose.yml up --build
```

Run tests in a separate terminal with:

```bash
poetry run pytest
```


## Documentation

Documentation can be built from the `/docs` folder:

```bash
cd docs
poetry run make <target>
```

Where `<target>` could be e.g. `html`. See `poetry run make` for additional options.


## License

Memoriam is copyright © 2020 Protojour AS, and is licensed under Apache License v2.0. See [LICENSE](https://github.com/protojour/memoriam/blob/master/LICENSE) for details.
