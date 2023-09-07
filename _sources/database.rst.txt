Database Schema
---------------

SkyPortal uses a PostgreSQL database to manage persistent state. This section
documents the schema of the database and describes how the application
interacts with it.

SQLAlchemy Model API Documentation
==================================

The SkyPortal Python backend interacts with the PostgreSQL backend using the
`SQLAlchemy <http://sqlalchemy.org>`_
`object relational mapper <https://docs.sqlalchemy.org/en/13/orm/tutorial.html>`_.
Each database table is represented by a Python class, and each table Column
is represented by a class attribute. This Section documents each of the
SkyPortal and baselayer classes that are mapped to database tables.

.. automodule:: skyportal.models
   :members:

.. automodule:: baselayer.app.models
   :members:

Entity Relationship Diagram
===========================

The following entity relationship diagram visualizes the structure of the
SkyPortal database.

.. image:: images/erd.png
   :alt: Skyportal Entity Relationship Diagram
   :target: _images/erd.png
