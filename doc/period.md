# Periodic Timeseries Features

Skyportal supports periodicity features. In particular, we provide a `Periodogram Analysis` button available from the `Source` page. This page allows for a dynamic, slider based period assignment and display.

![Periodogram page](images/periodogram.png)

The periods are saved as `Annotation`s, and the app searches for annotated periods with the keyword "period." For those sources with this annotation, the `SourceTable` includes a phase-folded light curve on that period.
