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
   :exclude-members: init_db, SlugifiedStr

Entity Relationship Diagram
===========================

The following entity relationship diagram visualizes the structure of the
SkyPortal database. Drag to pan, scroll to zoom, and click a table to highlight
the tables it is related to.

.. raw:: html

   <div class="erd">
     <div class="erd-bar">
       <div class="erd-find">
         <input class="erd-input" type="search" placeholder="Find a table"
                aria-label="Find a table" autocomplete="off" spellcheck="false">
         <ul class="erd-hits" hidden></ul>
       </div>
       <div class="erd-tools">
         <button type="button" class="erd-btn" data-erd="zoom-out" aria-label="Zoom out">&#8722;</button>
         <output class="erd-level">100%</output>
         <button type="button" class="erd-btn" data-erd="zoom-in" aria-label="Zoom in">+</button>
         <button type="button" class="erd-btn" data-erd="fit">Fit</button>
         <button type="button" class="erd-btn" data-erd="full">Fullscreen</button>
       </div>
     </div>
     <div class="erd-stage" tabindex="0" role="application" aria-label="Entity relationship diagram">

.. raw:: html
   :file: erd.svg

.. raw:: html

     </div>
     <p class="erd-status" role="status"></p>
     <div class="erd-detail" hidden></div>
     <div class="erd-rel" hidden></div>
   </div>

.. raw:: html
   :file: erd-data.html
