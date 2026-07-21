// Interactive localization viewer built on Aladin Lite v3.
//
// This replaces the former hand-rolled d3-geo "globe" (an SVG orthographic
// projection drawn with d3-geo-zoom). Aladin gives us a real HiPS sky
// background, native pan/zoom/projection controls, and proper celestial
// rendering, while we keep the same component contract (default export +
// props) so the existing consumers — GcnSelectionForm, ObservationPlan-
// RequestForm and ObservationPlanGlobe — need no changes.
//
// What we draw on top of the sky:
//   * the localization credible-region contour (50% / 90% outlines + center)
//   * instrument fields as clickable footprints (toggle the selected set)
//   * executed observations as clickable footprints
//   * sources and galaxies as clickable catalogs (labels + link-out)
//   * the Sun and Moon for observability context
//
// Aladin is loaded as an npm module and bundled by rspack (its WASM renderer
// is inlined in the dist, so no extra asset wiring is needed). `aladin-lite`
// ships no TypeScript types, so the Aladin objects below are loosely typed —
// only the public props are strictly typed, matching the d3-heavy code it
// replaces.
import { useEffect, useRef, useState } from "react";
import CircularProgress from "@mui/material/CircularProgress";
import Typography from "@mui/material/Typography";
import A from "aladin-lite";

import { moonGeoJSON, sunGeoJSON } from "../../utils";

// Aladin v3 renders through WebGL2 and throws if it is unavailable (headless
// browsers, software-rendering setups). Detect it up front so we can show a
// message instead of letting the renderer raise.
const hasWebGL2 = (): boolean => {
  try {
    return !!document.createElement("canvas").getContext("webgl2");
  } catch {
    return false;
  }
};

// ---------------------------------------------------------------------------
// Geometry helpers
// ---------------------------------------------------------------------------

// Aladin expects RA in [0, 360). GeoJSON longitudes may arrive negative.
const normRa = (ra: number): number => ((ra % 360) + 360) % 360;

// Flatten a GeoJSON feature's geometry into a list of rings, each ring being
// an array of [ra, dec] vertices. Instrument fields arrive as LineString
// boundaries (a single closed path), while skymap/observation contours can be
// Polygon/MultiPolygon; handle all of them.
const ringsOf = (feature: any): [number, number][][] => {
  const geom = feature?.geometry;
  if (!geom?.coordinates) return [];
  switch (geom.type) {
    case "Polygon":
      return geom.coordinates;
    case "MultiPolygon":
      return geom.coordinates.flat();
    case "LineString":
      return [geom.coordinates];
    case "MultiLineString":
      return geom.coordinates;
    default:
      return [];
  }
};

// Build Aladin polygon footprints from a GeoJSON object. Accepts either a
// single Feature (e.g. a skymap contour) or a FeatureCollection (e.g. an
// instrument field's `contour_summary` or an observation), expanding every
// ring of every contained feature into a polygon footprint.
const featurePolygons = (geojson: any, opts: any): any[] => {
  const features = geojson?.features ?? [geojson];
  return features.flatMap((feature: any) =>
    ringsOf(feature).map((ring) =>
      A.polygon(
        ring.map(([ra, dec]) => [normRa(ra), dec]),
        opts,
      ),
    ),
  );
};

// Deterministic color from a filter list (mirrors the previous d3 behavior so
// a given instrument keeps a stable, recognizable selected-field color).
const filtersToColor = (filters: string[] = []): string => {
  const filterStr = filters.join("");
  let hash = 0;
  for (let i = 0; i < filterStr.length; i += 1) {
    hash = filterStr.charCodeAt(i) + ((hash << 5) - hash);
  }
  let color = "#";
  for (let i = 0; i < 3; i += 1) {
    const value = (hash >> (i * 8)) & 0xff;
    color += `00${value.toString(16)}`.slice(-2);
  }
  return color;
};

// Rough field-of-view (deg) that comfortably frames the 90% contour.
const fovForContour = (contour: any): number => {
  const ring = ringsOf(contour?.features?.[2])[0];
  if (!ring?.length) return 60;
  const decs = ring.map((c) => c[1]);
  const ras = ring.map((c) => normRa(c[0]));
  const span = Math.max(
    Math.max(...decs) - Math.min(...decs),
    Math.max(...ras) - Math.min(...ras),
  );
  return Math.min(180, Math.max(2, span * 1.6));
};

interface LocalizationPlotProps {
  localization?: any;
  sources?: any;
  galaxies?: any;
  instrument?: any;
  observations?: any;
  airmass_threshold?: number;
  options?: any;
  height?: number;
  width?: number;
  // Retained for API compatibility with the previous d3 globe; Aladin manages
  // its own view, so these are accepted but unused.
  rotation?: any;
  setRotation?: (...a: any[]) => void;
  selectedFields?: number[];
  setSelectedFields?: (...a: any[]) => void;
  selectedObservations?: number[];
  setSelectedObservations?: (...a: any[]) => void;
  projection?: string | undefined;
}

// ---------------------------------------------------------------------------
// Aladin renderer
// ---------------------------------------------------------------------------

interface AladinGlobeProps {
  skymap?: any;
  sources?: any;
  galaxies?: any;
  instrument?: any;
  observations?: any;
  options: any;
  height: number;
  width: number;
  airmass_threshold: number;
  selectedFields: number[];
  setSelectedFields: (...a: any[]) => void;
  selectedObservations: number[];
  setSelectedObservations: (...a: any[]) => void;
  projection?: string;
}

const AladinGlobe = ({
  skymap = null,
  sources = null,
  galaxies = null,
  instrument = null,
  observations = null,
  options,
  height,
  width,
  airmass_threshold,
  selectedFields,
  setSelectedFields,
  selectedObservations,
  setSelectedObservations,
  projection = "orthographic",
}: AladinGlobeProps) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const aladinRef = useRef<any>(null);
  // Persistent layers, created once and cleared/repopulated on data changes.
  const layers = useRef<any>({});
  const didCenter = useRef(false);
  // Flips true once Aladin's async init resolves; gates the layer effects and
  // re-triggers them (it is in their dependency arrays).
  const [ready, setReady] = useState(false);
  const [supported] = useState(hasWebGL2);

  // The footprint-click handler is registered once but needs to see the latest
  // selection state and setters; keep them in a ref that updates every render.
  const live = useRef({
    selectedFields,
    setSelectedFields,
    selectedObservations,
    setSelectedObservations,
  });
  useEffect(() => {
    live.current = {
      selectedFields,
      setSelectedFields,
      selectedObservations,
      setSelectedObservations,
    };
  });

  // --- init once -----------------------------------------------------------
  useEffect(() => {
    if (!supported) return undefined;
    let cancelled = false;
    A.init.then(() => {
      if (cancelled || !containerRef.current || aladinRef.current) return;

      const center = skymap?.features?.[0]?.geometry?.coordinates;
      const aladin = A.aladin(containerRef.current, {
        survey: "P/DSS2/color",
        projection: projection === "mollweide" ? "MOL" : "SIN",
        cooFrame: "equatorial",
        fov: skymap ? fovForContour(skymap) : 180,
        target: center ? `${normRa(center[0])} ${center[1]}` : undefined,
        showReticle: false,
        // Minimal chrome: this is embedded in a narrow form column. Keep zoom +
        // fullscreen (so the operator can pop out to a detailed view) and drop
        // the controls that crowd a small inset.
        showZoomControl: true,
        showFullscreenControl: true,
        showLayersControl: false,
        showCooGridControl: false,
        showProjectionControl: false,
        showStatusBar: false,
      });
      aladinRef.current = aladin;

      // Create the persistent layers up front.
      layers.current.contour = A.graphicOverlay({
        name: "skymap",
        color: "black",
      });
      layers.current.fields = A.graphicOverlay({
        name: "fields",
        color: "blue",
      });
      layers.current.observations = A.graphicOverlay({
        name: "observations",
        color: "blue",
      });
      layers.current.sunMoon = A.graphicOverlay({ name: "sun/moon" });
      aladin.addOverlay(layers.current.contour);
      aladin.addOverlay(layers.current.fields);
      aladin.addOverlay(layers.current.observations);
      aladin.addOverlay(layers.current.sunMoon);

      layers.current.markers = A.catalog({
        name: "labels",
        shape: "cross",
        color: "cyan",
        sourceSize: 10,
        labelColumn: "name",
        labelColor: "white",
      });
      layers.current.sources = A.catalog({
        name: "sources",
        shape: "circle",
        color: "red",
        sourceSize: 8,
        onClick: "showPopup",
        labelColumn: "name",
        labelColor: "white",
      });
      layers.current.galaxies = A.catalog({
        name: "galaxies",
        shape: "circle",
        color: "lime",
        sourceSize: 8,
        onClick: "showPopup",
        labelColumn: "name",
        labelColor: "white",
      });
      aladin.addCatalog(layers.current.markers);
      aladin.addCatalog(layers.current.sources);
      aladin.addCatalog(layers.current.galaxies);

      // Clicking a footprint toggles the corresponding selection set. The
      // footprint id encodes which set it belongs to ("field:<id>" /
      // "obs:<id>"); React state changes then re-render the layer.
      aladin.on("footprintClicked", (arg: any) => {
        const fp = arg && arg.id !== undefined ? arg : (arg?.footprint ?? arg);
        const id: string | undefined = fp?.id;
        if (!id) return;
        const {
          selectedFields: sf,
          setSelectedFields: setSf,
          selectedObservations: so,
          setSelectedObservations: setSo,
        } = live.current;
        if (id.startsWith("field:")) {
          const fid = Number(id.slice(6));
          setSf(sf.includes(fid) ? sf.filter((x) => x !== fid) : [...sf, fid]);
        } else if (id.startsWith("obs:")) {
          const fid = Number(id.slice(4));
          setSo(so.includes(fid) ? so.filter((x) => x !== fid) : [...so, fid]);
        }
      });

      // Clicking a source/galaxy opens its SkyPortal page.
      aladin.on("objectClicked", (obj: any) => {
        const url = obj?.data?.url;
        if (url) window.open(url, "_blank", "noopener");
      });

      setReady(true);
    });
    return () => {
      cancelled = true;
    };
    // Mount once: Aladin is initialized a single time and the layer effects
    // below handle all subsequent data/selection updates.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // --- skymap contour ------------------------------------------------------
  useEffect(() => {
    if (!ready) return;
    const overlay = layers.current.contour;
    const markers = layers.current.markers;
    overlay.removeAll();
    const visible = options?.localization || options?.skymap;
    if (visible && skymap?.features) {
      // features: [0] center, [1] 50% region, [2] 90% region
      featurePolygons(skymap.features[2], {
        color: "black",
        lineWidth: 2,
      }).forEach((p) => overlay.addFootprints(p));
      featurePolygons(skymap.features[1], {
        color: "grey",
        lineWidth: 2,
      }).forEach((p) => overlay.addFootprints(p));
      const center = skymap.features[0]?.geometry?.coordinates;
      if (center) {
        markers.addSources([
          A.source(normRa(center[0]), center[1], { name: "Center" }),
        ]);
      }
      // Center the view on first data arrival.
      if (!didCenter.current && center) {
        aladinRef.current.gotoRaDec(normRa(center[0]), center[1]);
        aladinRef.current.setFoV(fovForContour(skymap));
        didCenter.current = true;
      }
    }
  }, [ready, skymap, options?.localization, options?.skymap]);

  // --- instrument fields ---------------------------------------------------
  useEffect(() => {
    if (!ready) return;
    const overlay = layers.current.fields;
    overlay.removeAll();
    if (options?.instrument && instrument?.fields) {
      const filterColor = filtersToColor(instrument.filters);
      const hasRef = instrument.fields.some(
        (f: any) => (f.reference_filters || []).length > 0,
      );
      instrument.fields.forEach((f: any) => {
        const fieldId = Number(f.field_id);
        const selected = selectedFields.includes(fieldId);
        const references = f.reference_filters || [];
        const fill = selected
          ? filterColor
          : f.airmass && f.airmass < airmass_threshold
            ? "white"
            : "gray";
        const opacity = hasRef && references.length === 0 ? 0.3 : 0.85;
        featurePolygons(f.contour_summary, {
          color: "blue",
          lineWidth: selected ? 3 : 1,
          fill: true,
          fillColor: fill,
          opacity,
        }).forEach((p) => {
          p.id = `field:${fieldId}`;
          overlay.addFootprints(p);
        });
      });
    }
  }, [
    ready,
    instrument,
    options?.instrument,
    selectedFields,
    airmass_threshold,
  ]);

  // --- executed observations ----------------------------------------------
  useEffect(() => {
    if (!ready) return;
    const overlay = layers.current.observations;
    overlay.removeAll();
    if (options?.observations && observations) {
      observations.forEach((f: any) => {
        const fieldId = f.properties?.field_id;
        const selected = selectedObservations.includes(fieldId);
        featurePolygons(f, {
          color: "blue",
          lineWidth: 1,
          fill: true,
          fillColor: selected ? "red" : "white",
          opacity: 0.6,
        }).forEach((p) => {
          p.id = `obs:${fieldId}`;
          overlay.addFootprints(p);
        });
      });
    }
  }, [ready, observations, options?.observations, selectedObservations]);

  // --- sources -------------------------------------------------------------
  useEffect(() => {
    if (!ready) return;
    const cat = layers.current.sources;
    cat.removeAll();
    if (options?.sources && sources?.features) {
      cat.addSources(
        sources.features.map((d: any) =>
          A.source(
            normRa(d.geometry.coordinates[0]),
            d.geometry.coordinates[1],
            { name: d.properties?.name, url: d.properties?.url },
          ),
        ),
      );
    }
  }, [ready, sources, options?.sources]);

  // --- galaxies ------------------------------------------------------------
  useEffect(() => {
    if (!ready) return;
    const cat = layers.current.galaxies;
    cat.removeAll();
    if (options?.galaxies && galaxies?.features) {
      cat.addSources(
        galaxies.features.map((d: any) =>
          A.source(
            normRa(d.geometry.coordinates[0]),
            d.geometry.coordinates[1],
            { name: d.properties?.name, url: d.properties?.url },
          ),
        ),
      );
    }
  }, [ready, galaxies, options?.galaxies]);

  // --- sun & moon ----------------------------------------------------------
  useEffect(() => {
    if (!ready) return;
    const overlay = layers.current.sunMoon;
    const markers = layers.current.markers;
    overlay.removeAll();
    const now = new Date();
    [
      {
        body: sunGeoJSON(now),
        color: "yellow",
        fill: "rgba(255,255,0,0.6)",
        label: "Sun",
      },
      {
        body: moonGeoJSON(now),
        color: "darkgray",
        fill: "rgba(150,150,150,0.6)",
        label: "Moon",
      },
    ].forEach(({ body, color, fill, label }) => {
      const [lon, dec] = body?.geometry?.coordinates ?? [];
      const radius = body?.properties?.radius;
      if (lon === undefined || dec === undefined) return;
      const ra = normRa(lon);
      overlay.addFootprints(
        A.circle(ra, dec, Math.max(radius || 0, 0.3), {
          color,
          fillColor: fill,
        }),
      );
      markers.addSources([A.source(ra, dec, { name: label })]);
    });
  }, [ready]);

  if (!supported) {
    return (
      <Typography variant="body2" color="textSecondary">
        This sky view requires WebGL2, which is not available in this browser.
      </Typography>
    );
  }

  // Fill the parent column (consumers embed this in a narrow grid cell) as a
  // square, capped at the requested size — mirroring the old SVG's responsive
  // viewBox behavior rather than forcing a fixed pixel box that overflows.
  return (
    <div
      ref={containerRef}
      style={{
        width: "100%",
        maxWidth: `${width}px`,
        maxHeight: `${height}px`,
        aspectRatio: "1 / 1",
      }}
    />
  );
};

// ---------------------------------------------------------------------------
// Public wrapper: resolves the localization (prop or redux) and gates on load.
// ---------------------------------------------------------------------------

const LocalizationPlot = ({
  localization = null,
  sources = null,
  galaxies = null,
  instrument = null,
  observations = null,
  airmass_threshold = 2.5,
  options = {
    localization: false,
    sources: false,
    galaxies: false,
    instrument: false,
    observations: false,
  },
  height = 600,
  width = 600,
  selectedFields = [],
  setSelectedFields = () => {},
  selectedObservations = [],
  setSelectedObservations = () => {},
  projection = "orthographic",
}: LocalizationPlotProps) => {
  if (
    !localization?.id ||
    !localization?.dateobs ||
    !localization?.localization_name ||
    !localization?.contour
  ) {
    return <CircularProgress />;
  }

  return (
    <AladinGlobe
      skymap={localization.contour}
      sources={sources?.geojson}
      galaxies={galaxies?.geojson}
      instrument={instrument}
      observations={observations?.geojson}
      options={options}
      height={height}
      width={width}
      airmass_threshold={airmass_threshold}
      selectedFields={selectedFields}
      setSelectedFields={setSelectedFields}
      selectedObservations={selectedObservations}
      setSelectedObservations={setSelectedObservations}
      projection={projection}
    />
  );
};

export default LocalizationPlot;
