# Architecture

This document describes the high-level architecture of SkyPortal.
If you want to familiarize yourself with the code base, you are just in the right place!

See also the [feature guide](./doc/adding_features.md), which walks through specifics of the code base, as well as the [developer guide](./doc/dev.md), which has notes on code styling and testing.

## Bird's Eye View

SkyPortal is an example of a Target and Observation Manager (TOM), which , are designed to support the astronomical community to efficiently work with astronomical data sets, identify sources of interest, and obtain follow-up. It aims to be a sophisticated ``full-stack transient ecosystem'' that integrates capabilities of telescope scheduling, observing optimization, spatial catalogs, astronomical data analysis, and others into a single software stack.

## Front-end

The SkyPortal front-end uses React, a component-based UI library, in conjunction with Redux, a front-end state-management library.

Each component definition typically goes in its own file in `static/js/components`.

SkyPortal bundles all Redux-related code (action types, action creators, reducer) associated with a particular branch of the application state together in a file in the `static/js/ducks` directory ([read more about "ducks" modules here](https://github.com/erikras/ducks-modular-redux)).

SkyPortal hydrates new tabs using the redux state of previous tabs to minimize redundant interactions with the server.

## Back-end

The SkyPortal back-end is built using [Tornado](https://www.tornadoweb.org/en/stable/), a Python web application framework that provides its own I/O event loop for non-blocking sockets, making it ideal for use with websockets.

To handle HTTP requests, we define _request handlers_ that are mapped to API endpoints in the application's configuration (in `skyportal/app_server.py` -- see below). Each SkyPortal request handler is a subclass of
BaseHandler`(defined in`skyportal/handlers/base.py`), a handler that extends Tornado's base [RequestHandler](https://www.tornadoweb.org/en/stable/web.html#tornado.web.RequestHandler), handling authentication and providing utility methods for pushing websocket messages to the front-end and returning HTTP responses.

Handlers appear in the directory `skyportal/handlers/api`.

## Database

SkyPortal uses a PostgreSQL database to manage persistent state. The SkyPortal Python backend interacts with the PostgreSQL backend using the
`SQLAlchemy <http://sqlalchemy.org>`_
`object relational mapper <https://docs.sqlalchemy.org/en/20/orm/tutorial.html>`_.
Each database table is represented by a Python class, and each table Column
is represented by a class attribute.

The models defined in SkyPortal can be found in the directory `skyportal/models`, while those found in baselayer can be found in `baselayer/app/models.py`.

When adding a new model, database migrations will be key. In addition to the Database Migrations section, which describes how to create migration files locally, one of the GitHub actions automatically will create the alembic migration file, which should then be committed in the directory `alembic/versions`.

## Permissions

SkyPortal has permissions on handler interactions. For example, the decorator `@auth_or_token` tells the application that the request must either come from a logged in user (via the browser), or must include a valid token in the request header. If neither of these are true, the request returns with an error. There are also specific permissions for interactions within the app (in `skyportal/model_util.py`), that can be assigned to users and then specified in a handler as follows:

```
from baselayer.app.access import permissions
@permissions(["System admin"])
```

It also has permissions on the database models. In SkyPortal, RLS policies are defined on SQLAlchemy mapped classes. Each class has a single policy for each of the create, delete, update, and read access modes. Records are read- and create-public by default, and update- and delete-restricted (i.e., only accessible to users with the "System admin" ACL) by default. Join table classes are also update- and delete-restricted by default, but they can (by default) be created or read by any user that can read both their left and right records. These defaults can be overridden on any mapped class.

## Microservices

SkyPortal uses a microservice architecture managed with supervisord, which allows for running multiple instances of the application in parallel to ensure availability and reduce downtime. Moreover, we can add microservices to run background operations continuously. This is used to run the application, as well as the database migration manager, the webpack builder, websocket server, cron jobs, external logging, and nginx. It is also used when adding computationally expensive or long-running features such as the ingestion of GCN events with low latency, processing of observation plans, sending notifications and reminders, and programming recurrent API calls. These services and others can be found in the directory `services/` in both SkyPortal and baselayer.

## Testing

SkyPortal has a test suite, which appear in the directory `skyportal/tests`. They are generally broken down into front-end and back-end, however, there is also a `flaky` directory for tests that do not always pass, such as those with external interactions. The [developer guide](./doc/dev.md) contains more information on test infrastructure.

## Plotting

SkyPortal uses [plotly](https://github.com/plotly/plotly.py) for interactive plotting. Examples include the photometry plot (in `/components/PhotometryPlot.jsx`) and spectroscopy plot (in `/components/SpectraPlot.jsx`). [Vega-lite](https://vega.github.io/) is used for simple, lightweight plots requiring minimal customization and fast render times, such as for the photometry plot on the candidates page (in `static/js/components/VegaPhotometry.jsx`).
