# Versioning

SkyPortal being an API-based service, its version number should have a meaning for the end-user AND the developer or system administrator that will deploy it. On the other hand, maintaining 2 distinct version numbers would not be practical.

The development cycle of SkyPortal is such that breaking API changes are rare, as we often add, improve, refactor, or fix existing features rather than change their output or behavior. Version changes of critical system dependencies are also very rare (e.g. upgrading the version of PostgreSQL or the Python runtime). On the other hand, new features (new endpoints, new tables, additional data returned by existing endpoints) are added more frequently. Lastly, changes that do not impact the user nor the developer (e.g. refactoring, performance improvements, bug fixes) are very common, but do not necessarily need to be advertised to the end-user.

Based on these considerations, we have decided to use [Semantic Versioning](https://semver.org/) for SkyPortal. The version number will be of the form `MAJOR.MINOR.PATCH`, where:

- `MAJOR` is incremented when breaking changes are introduced, for the user or the developer
- `MINOR` is incremented when new features are added in a backwards-compatible manner, requiring no changes to the user's code and minimal changes to the deployment
- `PATCH` is incremented when backwards-compatible bug fixes are introduced, or when changes are made that do not impact the user nor the developer

The development of SkyPortal is active enough that it would be impractical to update the version number for every commit. Instead, we will update the version number along with a release on GitHub that tags a specific commit in the repository, at most one a week. That way, the developer / system admin can easily checkout to the latest tagged release's commit (when there is a new version available) rather than simply point to whatever is on main. The end-user can always easily check which version of SkyPortal they are querying/using, as it is returned in every API response and displayed on the about page of the web application.

Each instance of SkyPortal is responsible for updating the version of the software they are running, but it is good to keep in mind that the lastest version of SkyPortal is always available on GitHub, and that the latest version number is also visible at the top left of the [Documentation](https://skyportal.io/docs) page.

The version number will be updated in the `skyportal/__init__.py` file, and release notes will be posted with the tagged release.

As a SkyPortal, please refer to the [Developer Guide](dev) for more information on how to interact with the codebase, and to the [Deployment Guide](deploy) for more information on how to deploy SkyPortal.
