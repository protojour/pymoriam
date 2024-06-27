FROM python:3.11-slim-bookworm as docs

WORKDIR /srv/docs

RUN apt-get update && apt-get install --no-install-recommends -y make

RUN pip install poetry>=1.7.0
COPY docs /srv/docs/docs
COPY onto/SchemaGuide.md /srv/docs/onto/SchemaGuide.md
COPY pyproject.toml poetry.lock /srv/docs/
RUN poetry install --only docs && \
    cd docs && poetry run make html


FROM python:3.11-slim-bookworm as dist

WORKDIR /srv/memoriam

ENV PYHTONPATH /srv/memoriam
ENV PYTHONUNBUFFERED 1
ENV PYTHONOPTIMIZE 1
ENV PYTHONWARNINGS "ignore::DeprecationWarning"

RUN apt-get update && apt-get install --no-install-recommends -y build-essential libffi-dev libyaml-dev curl
RUN curl -sSf https://sh.rustup.rs | bash -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

ADD https://download.arangodb.com/arangodb311/Community/Linux/arangodb3-client_3.11.9-1_amd64.deb /srv/memoriam/arango_client.deb
RUN dpkg -i arango_client.deb && \
    rm arango_client.deb

RUN pip install poetry>=1.7.0 && \
    poetry config virtualenvs.in-project true
COPY pyproject.toml poetry.lock /srv/memoriam/
RUN poetry install --only main && \
    apt-get autoremove -y build-essential curl

COPY memoriam /srv/memoriam/memoriam/
RUN poetry install --only-root

COPY LICENSE README.md CHANGELOG.md /srv/memoriam/
COPY static /srv/memoriam/static
COPY onto/build /srv/memoriam/onto
COPY --from=docs /srv/docs/docs/_build/html /srv/memoriam/docs

ENTRYPOINT ["poetry", "run"]
CMD ["memoriam"]
