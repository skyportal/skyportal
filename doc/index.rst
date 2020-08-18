SkyPortal
---------

SkyPortal is an extensible data platform that allows astronomers to
visualize and discuss light curves and spectra, augment those
measurements with classifications and other meta-data, and to
coordinate follow-up observations.

|github| |license| |build-status| |joss|

.. |github| image:: https://img.shields.io/badge/GitHub-skyportal%2Fskyportal-blue
   :target: https://github.com/skyportal/skyportal

.. |license| image:: https://img.shields.io/badge/License-BSD%203--Clause-blue.svg
   :target: https://github.com/skyportal/skyportal/LICENSE.txt

.. |build-status| image:: https://github.com/skyportal/skyportal/workflows/Test%20SkyPortal/badge.svg
   :target: https://github.com/skyportal/skyportal/actions?query=workflow%3A%22Test+SkyPortal%22+branch%3Amaster

.. |joss| image:: http://joss.theoj.org/papers/10.21105/joss.01247/status.svg
   :target: https://github.com/skyportal/skyportal/workflows/Test%20SkyPortal/badge.svg

.. image:: ../static/images/skyportal_responsive.jpg
   :alt: SkyPortal

The project is motivated by the Large Synoptic Survey Telescope
project (LSST; starting in 2021), which will generate ~20 TB and
detect 100 million sources every night.  The LSST promises to be a
gateway through which a diverse set of time-variable sources and
transient events will be understood.

In order to make this rich but complex data source more accessible, we
built SkyPortal to display light curves and spectra in an
intuitive and easily-accessible format, allow for subsequent
annotation and post-processing, provide an API to do machine-based
access to the data, and to allow subsequent dissemination of the
results—either to other SkyPortal instances, or to trigger follow-up
by instruments or humans.

Quick Start
-----------

To launch a demo instance of SkyPortal, first `clone the source code from
GitHub <https://github.com/skyportal/skyportal>`_:

.. code-block:: bash

  $ git clone git@github.com:skyportal/skyportal.git

then install the `system dependencies <./setup.html#dependencies>`_. From the
``skyportal`` directory, run

.. code-block:: bash

  $ make run

When the terminal shows ``Server at: http://localhost:5000``, open another
terminal, navigate to the ``skyportal`` directory, and run

.. code-block:: bash

  $ make load_demo_data

to populate the database with sample data. To access the running, populated
skyportal instance, navigate your browser to: ``http://localhost:5000``.

User Guide
----------

.. toctree::
   :maxdepth: 1

   design
   setup
   usage
   api
   dev
   deploy
   data_loader
   contributing
   adding_features
   styling

Contributing
============

SkyPortal is released under the BSD license.  We encourage you to
modify it, reuse it, and contributed changes back for the benefit of
others.  We follow standard open source development practices: changes
are submitted as pull requests and, once they pass the test suite,
reviewed by the team before inclusion.  Please also see
`our contributing guide <./contributing.html>`_.


.. Indices and tables
.. ==================

.. * :ref:`genindex`
.. * :ref:`modindex`
.. * :ref:`search`
