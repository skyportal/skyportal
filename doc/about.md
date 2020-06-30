# About

SkyPortal is an extensible data platform that allows researchers to
discuss light curve measurements, augment those measurements with
classification and other meta-data, and to coordinate follow-up.

The project is motivated by the Large Synoptic Survey Telescope
project (LSST; starting in 2021), which will generate ~20 TB and
detect 100 million sources every night.  The LSST promises to be a
gateway through which a diverse set of time-variable sources and
transient events will be understood.

In order to make this rich but complex data source more accessible, we
built SkyPortal to filter event streams, publish light curves in an
intuitive and easily-accessible format, allow for subsequent
annotation and post-processing, provide an API to do machine-based
access to the data, and to allow subsequent dissemination of the
results—either to other SkyPortal instances, or to trigger follow-up
by instruments or humans.

SkyPortal is designed to be effective, fast, and scalable.  The
following diagram shows the underlying architecture:

![System architecture](images/architecture.png)

All the technological components used in SkyPortal are applied exactly
for the purpose they were written.  We do not attempt novel
configurations that push these technologies outside of their design
boundaries.  Instead, we combine technologies effectively to build a
robust and scalable platform, so that many of the components could be
replaced, should they become unsupported.

The frontend is built on React, using Redux to drive the application
logic, as shown in the following diagram:

![Frontend architecture](images/frontend.png)

SkyPortal is released under the BSD license.  We encourage you to
modify it, reuse it, and contributed changes back for the benefit of
others.  We follow standard open source development practices: changes
are submitted as pull requests and, once they pass the test suite,
reviewed by the team before inclusion.  Please also see
[our contributing guide](contributing).
