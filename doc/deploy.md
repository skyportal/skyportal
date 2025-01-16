# Deployment

SkyPortal can be deployed either with or without using Docker.
Without Docker, all services (such as the database) need to be running
locally, as described in [setup](setup).

More commonly, production deployment will use Docker images. Here, we
discuss how to deploy via
[docker-compose](https://docs.docker.com/compose/), but much of the
same information applies when using Kubernetes, for which we have an
[example deployment](https://github.com/skyportal/deploy).

## Building the Docker images

The first step is to create the images to launch. For that, you can start by git cloning the repository and checking out to the desired version. For a production deployment, we recommend using the version tagged on a release (see [versioning](versioning)).

After customizing your `docker.yaml` file (the equivalent of `config.yaml`, used as the config file when building a docker image), you may build the images using the following command:

```
make docker-local
```

## Starting containers

Next, we deploy two containers: `web` (the SkyPortal application, which image you just built) and
`db` (the PostgreSQL server, from the official Docker image).
The database is stored and persisted in a local docker volume called `skyportal_dbdata` (see `docker volume ls`), which location is specified in the `docker-compose.yaml` file, as well as the database name, user, and password, other volume mounts, and the port mapping.

To start the containers, run:
```
docker-compose up -d
```

The application will not be accessible until the database has been initialized, which is explained in the next section.

## Initializing the database

Note that by default, the SkyPortal image will run the application in production (`make run_production`, see the `CMD` directive at the end of the Dockerfile).

The key behavior to note when running production mode is that the application will not create any database tables automatically (to avoid messing with production data). This means that the very first time you spin up SkyPortal using containers, the `skyportal_dbdata` volume will only have an empty database. While the `skyportal-web-1` container will start, the web application will not be accessible without an initialized database. This can easily be done manually, and the easiest way to do this is to run:

To initialize an empty database, run:
```
docker exec skyportal-web-1 bash -c 'source /skyportal_env/bin/activate && FLAGS="--config=config.yaml" make db_create_tables'
```

To load an example database, run:
```
docker exec skyportal-web-1 bash -c 'source /skyportal_env/bin/activate && FLAGS="--create_tables --config=config.yaml" make load_demo_data'
```

*Notes:*

- This command can take a few minutes to run, depending on your machine's configuration.
- It should only **run once**.
- Older versions of docker compose may use a different container name, such as `skyportal_web_1` (with underscores instead of dashes).
- The `FLAGS` variable is used to pass arguments to the `make` command. In this case, we are passing the `--create_tables` flag to create the database tables and the `--config=config.yaml` flag to specify the configuration file to use. You can pass any other flags you want to the `make` command in the same way.
- If you are using a different configuration file, please refer to the next section on how to customize the deployment configuration, before you run the `make load_demo_data` command.
- When running the command above, you might see a few `SAWarning` warnings. These are harmless and can be ignored.
- Similarly, you might see a handful of `No token specified; reading from SkyPortal generated .tokens.yaml` messages. These appear as after creating the tables, the application will take a few seconds to start up and generate a token for the admin user. This token is then saved to a `.tokens.yaml` file in the root directory of the application. This token is used to authenticate the admin user when making requests to the API. The token is only generated once, and if you delete the `.tokens.yaml` file, a new token will be generated the next time the application starts up.

Now, you may browse to SkyPortal at `http://localhost:5000` (or any other port you have configured it to run on).

## Customizing the deployment configuration

If you want to use a specific configuration file at runtime (that can then be different from the one used to build the image), you can mount it as a volume when starting the container. For example, if you had a `config.yaml` file in a directory called `config`, you would add to your `docker-compose.yaml` file:

```yaml
    web:
        ...
        volumes:
        - ./config/config.yaml:/etc/skyportal/config.yaml
    ```
```
This will mount the `config.yaml` file from the `config` directory to the `/etc/skyportal/config.yaml` path in the container. You could technically directly have it mounted to `/skyportal/config.yaml`, but we recommend using a different path to not lose track of the original configuration file used to build the image.

You would need to pass the `--config=config.yaml` flag when calling any `make` commands. For the container to use this configuration file on startup, set the FLAG environment variable in the `docker-compose.yaml` file:

```yaml
    web:
        ...
        environment:
        - FLAGS=--config=/etc/skyportal/config.yaml
```

**Note: Elements of the configuration used to customize the frontend need to be set in the configuration file used to build the image (`docker.yaml`), as they are used to build the web application's bundle which only happens once at build time, and will not take effect if changed at runtime.**

## Handling problems

You can see which containers are running with `docker-compose ps`.

Inspect the logs for the running containers using:

```
docker-compose logs web
docker-compose logs db
```

(Or, follow the logs with `docker-compose logs -f db`.)

## Stopping the deployment

You may stop both containers using:

```
docker-compose stop
```

Or stop and remove them using:

```
docker-compose down
```

This does not affect data, which lives in the `./dbdata` directory.

## Updating the deployment

SkyPortal uses semantic versioning (see [versioning](versioning) below) to indicate API breaks. While the `main` branch is typically usable, we recommend rather using release versions, which aim to provide tested, stable development snapshots.

After initial deployment, it is important to verify that the current database schema has been stamped using Alembic (see [Database migrations](migrations)). Thereafter, the migration manager service will automatically apply pending migration scripts upon application restart.
