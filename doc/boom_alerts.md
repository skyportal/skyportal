# BOOM alert pages

With a BOOM alert broker configured (see the `boom` config section), SkyPortal
gains pages for searching and inspecting raw survey alerts.

## Pages

- `/alerts` — search alerts by object ID or sky position (cone search) for a
  given survey.
- `/alerts/:survey/:id` — detail page for one alert: photometry, metadata, and
  image cutouts. Cutouts arrive as gzipped FITS and are rendered client-side
  (`static/js/utils/imageProcessing.js`), so no server-side thumbnail
  generation is involved. From here an alert can be saved as a SkyPortal
  source, and its photometry copied to an existing source.

Both routes are registered through the config-driven `app.routes` list, so
deployments that do not use BOOM can omit them.

On the source page, a search menu (mounted via the `SourcePlugins` extension
point) links to alert searches at the source position.

## API

- `GET /api/boom/surveys/<survey>/alerts` — query a survey's alerts by object
  ID or position.
- `GET /api/boom/surveys/<survey>/alerts/cutouts` — fetch alert image cutouts.

The corresponding API tests require a reachable BOOM instance seeded with
reference data and skip themselves otherwise.
