# Versioning

Breaking API changes, and changes that require major upgrades of critical system dependencies (like PostgreSQL), are rare. On the other hand, features (new endpoints, or additional data returned by existing endpoints) are added regularly. Lastly, changes that impact neither the user nor the developer (e.g. refactoring, performance improvements, bug fixes) happen continuously, but do not typically need to be advertised.

SkyPortal uses [Semantic Versioning](https://semver.org/) to indicate the severity of changes. The version number will be of the form `MAJOR.MINOR.PATCH`, where:

- `MAJOR` is incremented when breaking changes, or major dependency upgrades, are introduced;
- `MINOR` is incremented when new features are added in a backwards-compatible manner, requiring no changes to user code and minimal changes to existing deployments; and
- `PATCH` is incremented when backwards-compatible bug fixes are made.

We aim to make releases monthly. New features are added earlier in the release cycle, then tested, with bugfixes made as necessary. New versions are published on GitHub, generated from tagged commits in the repository. System administrators would typically deploy directly from the tag. End-users can see, from within SkyPortal, which version they are querying: this information is included in API responses, as well as on the About page.

The SkyPortal version number is accessible as `skyportal.__version__`.

Please refer to the [Development Guide](dev)'s [Making a release](dev.html#making-a-release) section for instructions on how to create and publish a new release.
