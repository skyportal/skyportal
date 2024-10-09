# Versioning

Breaking API changes, and changes that require major upgrades of critical system dependencies (like PostgreSQL), are rare. On the other hand, features (new endpoints, or additional data returned by existing endpoints) are added regularly. Lastly, changes that impact neither the user nor the developer (e.g. refactoring, performance improvements, bug fixes) happen continuously, but do not typically need to be advertised.

SkyPortal uses [Semantic Versioning](https://semver.org/) to indicate the severity of changes. The version number will be of the form `MAJOR.MINOR.PATCH`, where:

- `MAJOR` is incremented when breaking changes, or major dependency upgrades, are introduced;
- `MINOR` is incremented when new features are added in a backwards-compatible manner, requiring no changes to user code and minimal changes to existing deployments; and
- `PATCH` is incremented when backwards-compatible bug fixes are made.

The development of SkyPortal is active enough that it would be impractical to update the version number for every commit. Instead, we aim for a monthly cadence. New features will be added earlier on in the cycle, then tested, and bugfixes implemented if necessary. We update the version number along with a signed release on GitHub pointing to a specific commit in the repository. That way, the developer / system admin of a SkyPortal instance can easily checkout to the latest tagged release's commit rather than directly point to the main branch's last commit. The end-user can easily check which version of SkyPortal they are querying, as it is returned in every API response. New versions will also be announced using the **Discussions** page of the repository. The latest available version number is also visible at the top left of the [Documentation](https://skyportal.io/docs) page.

The SkyPortal version number is accessible as `skyportal.__version__`.

Please refer to the [Deployment Guide](deploy) for more information on how to deploy SkyPortal.
