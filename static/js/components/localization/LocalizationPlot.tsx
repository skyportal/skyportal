import { useEffect, useRef, useState } from "react";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import Typography from "@mui/material/Typography";
import A from "aladin-lite";

import { galacticToEquatorial, moonPosition, sunPosition } from "../../utils";

// A.init rejects without WebGL2 and would surface as a page error wherever this is imported.
A.init.catch(() => {});

const hasWebGL2 = () => {
  try {
    return !!document.createElement("canvas").getContext("webgl2");
  } catch {
    return false;
  }
};

const normRa = (ra: number) => ((ra % 360) + 360) % 360;

const ringsOf = (feature: any): [number, number][][] => {
  const { type, coordinates } = feature?.geometry ?? {};
  if (!coordinates) return [];
  if (type === "MultiPolygon") return coordinates.flat();
  if (type === "LineString") return [coordinates];
  return ["Polygon", "MultiLineString"].includes(type) ? coordinates : [];
};

const featurePolygons = (geojson: any, opts: any, id?: string): any[] =>
  (geojson?.features ?? [geojson]).flatMap((feature: any) =>
    ringsOf(feature).map((ring) =>
      Object.assign(
        A.polygon(
          ring.map(([ra, dec]) => [normRa(ra), dec]),
          opts,
        ),
        id && { id },
      ),
    ),
  );

const filtersToColor = (filters: string[] = []) => {
  let hash = 0;
  for (const char of filters.join("")) {
    hash = char.charCodeAt(0) + ((hash << 5) - hash);
  }
  return `#${[0, 8, 16]
    .map((shift) => ((hash >> shift) & 0xff).toString(16).padStart(2, "0"))
    .join("")}`;
};

const toggleIn = (list: number[], id: number) =>
  list.includes(id) ? list.filter((x) => x !== id) : [...list, id];

const toCatalogSources = (geojson: any) =>
  geojson.features.map((d: any) =>
    A.source(normRa(d.geometry.coordinates[0]), d.geometry.coordinates[1], {
      name: d.properties?.name,
      url: d.properties?.url,
    }),
  );

const drawSunMoon = (source: any, ctx: CanvasRenderingContext2D) => {
  const r = 8;
  ctx.save();
  ctx.translate(source.x, source.y);
  ctx.beginPath();
  ctx.arc(0, 0, r, 0, 2 * Math.PI);
  if (source.data.body === "sun") {
    ctx.shadowColor = "rgba(255, 190, 0, 0.9)";
    ctx.shadowBlur = 12;
    ctx.fillStyle = "#ffd60a";
    ctx.fill();
  } else {
    const { fraction, angle } = source.data;
    ctx.fillStyle = "#3a3a3a";
    ctx.strokeStyle = "#9e9e9e";
    ctx.lineWidth = 1;
    ctx.fill();
    ctx.stroke();
    // angle is a position angle (north through east) and Aladin draws east on the left.
    ctx.rotate(Math.atan2(-Math.cos(angle), -Math.sin(angle)));
    ctx.beginPath();
    ctx.arc(0, 0, r, -Math.PI / 2, Math.PI / 2);
    const k = 2 * fraction - 1;
    ctx.ellipse(0, 0, r * Math.abs(k), r, 0, Math.PI / 2, -Math.PI / 2, k < 0);
    ctx.fillStyle = "#f2f2f2";
    ctx.fill();
  }
  ctx.restore();
};

const span = (values: number[]) => Math.max(...values) - Math.min(...values);

const fovForContour = (contour: any) => {
  const ring = ringsOf(contour?.features?.[2])[0];
  if (!ring?.length) return 60;
  const size = Math.max(
    span(ring.map((c) => c[1])),
    span(ring.map((c) => normRa(c[0]))),
  );
  return Math.min(180, Math.max(2, 1.6 * size));
};

interface LocalizationPlotProps {
  localization?: any;
  sources?: any;
  galaxies?: any;
  instrument?: any;
  observations?: any;
  airmass_threshold?: number;
  options?: Partial<
    Record<
      | "localization"
      | "sources"
      | "galaxies"
      | "instrument"
      | "observations"
      | "sun_moon"
      | "galactic_plane",
      boolean
    >
  >;
  height?: number;
  width?: number;
  selectedFields?: number[];
  setSelectedFields?: (fields: number[]) => void;
  selectedObservations?: number[];
  setSelectedObservations?: (observations: number[]) => void;
  projection?: string | undefined;
}

const AladinGlobe = ({
  localization,
  sources = null,
  galaxies = null,
  instrument = null,
  observations = null,
  airmass_threshold = 2.5,
  options = {},
  height = 600,
  width = 600,
  selectedFields = [],
  setSelectedFields = () => {},
  selectedObservations = [],
  setSelectedObservations = () => {},
  projection = "orthographic",
}: LocalizationPlotProps) => {
  const skymap = localization.contour;
  const containerRef = useRef<HTMLDivElement | null>(null);
  const aladinRef = useRef<any>(null);
  const layers = useRef<any>({});
  const [ready, setReady] = useState(false);
  const [supported] = useState(hasWebGL2);

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

  useEffect(() => {
    if (!supported) return undefined;
    let cancelled = false;
    const container = containerRef.current;
    A.init
      .then(() => {
        if (cancelled || !containerRef.current || aladinRef.current) return;
        const center = skymap.features?.[0]?.geometry?.coordinates;
        const aladin = A.aladin(containerRef.current, {
          survey: "P/DSS2/color",
          projection: projection === "mollweide" ? "MOL" : "SIN",
          cooFrame: "equatorial",
          fov: fovForContour(skymap),
          target: center && `${normRa(center[0])} ${center[1]}`,
          showReticle: false,
          showZoomControl: true,
          showFullscreenControl: true,
          showLayersControl: false,
          showCooGridControl: false,
          showProjectionControl: false,
          showStatusBar: false,
        });
        aladinRef.current = aladin;

        const overlay = (name: string, color: string) => {
          const layer = A.graphicOverlay({ name, color });
          aladin.addOverlay(layer);
          return layer;
        };
        const catalog = (opts: Record<string, any>) => {
          const layer = A.catalog({
            labelColumn: "name",
            labelColor: "white",
            ...opts,
          });
          aladin.addCatalog(layer);
          return layer;
        };
        layers.current = {
          contour: overlay("skymap", "black"),
          fields: overlay("fields", "blue"),
          observations: overlay("observations", "blue"),
          galacticPlane: overlay("galactic plane", "magenta"),
          // Before setReady: show()/hide() on a MOC not yet registered throws in the WASM core.
          sunExclusion: A.MOCFromCone(
            { ...sunPosition(new Date()), radius: 50 },
            {
              name: "sun exclusion",
              color: "yellow",
              fill: true,
              opacity: 0.15,
            },
          ),
          markers: catalog({
            name: "labels",
            shape: "cross",
            color: "cyan",
            sourceSize: 10,
          }),
          sources: catalog({
            name: "sources",
            shape: "circle",
            color: "red",
            sourceSize: 8,
            onClick: "showPopup",
          }),
          galaxies: catalog({
            name: "galaxies",
            shape: "circle",
            color: "lime",
            sourceSize: 8,
            onClick: "showPopup",
          }),
          sunMoon: catalog({
            name: "sun/moon",
            shape: drawSunMoon,
            sourceSize: 16,
            displayLabel: true,
          }),
        };
        aladin.addMOC(layers.current.sunExclusion);

        aladin.on("footprintClicked", (arg: any) => {
          const [kind, value] = (arg?.id ?? arg?.footprint?.id ?? "").split(
            ":",
          );
          const id = Number(value);
          const { selectedFields: sf, selectedObservations: so } = live.current;
          if (kind === "field")
            live.current.setSelectedFields(toggleIn(sf, id));
          if (kind === "obs")
            live.current.setSelectedObservations(toggleIn(so, id));
        });
        aladin.on("objectClicked", (obj: any) => {
          if (obj?.data?.url) window.open(obj.data.url, "_blank", "noopener");
        });
        setReady(true);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
      container
        ?.querySelectorAll<HTMLCanvasElement>("canvas.aladin-imageCanvas")
        .forEach((canvas) =>
          canvas
            .getContext("webgl2")
            ?.getExtension("WEBGL_lose_context")
            ?.loseContext(),
        );
      container?.replaceChildren();
      aladinRef.current = null;
      layers.current = {};
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!ready) return;
    const { contour, markers } = layers.current;
    contour.removeAll();
    markers.removeAll();
    if (!options.localization) return;
    const [center, region50, region90] = skymap.features ?? [];
    contour.addFootprints([
      ...featurePolygons(region90, { color: "black", lineWidth: 2 }),
      ...featurePolygons(region50, { color: "grey", lineWidth: 2 }),
    ]);
    const coords = center?.geometry?.coordinates;
    if (coords) {
      markers.addSources([
        A.source(normRa(coords[0]), coords[1], { name: "Center" }),
      ]);
    }
  }, [ready, skymap, options.localization]);

  useEffect(() => {
    if (!ready) return;
    const { fields } = layers.current;
    fields.removeAll();
    if (!options.instrument || !instrument?.fields) return;
    const filterColor = filtersToColor(instrument.filters);
    const hasRef = instrument.fields.some(
      (f: any) => f.reference_filters?.length,
    );
    instrument.fields.forEach((f: any) => {
      const fieldId = Number(f.field_id);
      const selected = selectedFields.includes(fieldId);
      const fillColor = selected
        ? filterColor
        : f.airmass && f.airmass < airmass_threshold
          ? "white"
          : "gray";
      fields.addFootprints(
        featurePolygons(
          f.contour_summary,
          {
            color: "blue",
            lineWidth: selected ? 3 : 1,
            fill: true,
            fillColor,
            opacity: hasRef && !f.reference_filters?.length ? 0.3 : 0.85,
          },
          `field:${fieldId}`,
        ),
      );
    });
  }, [
    ready,
    instrument,
    options.instrument,
    selectedFields,
    airmass_threshold,
  ]);

  useEffect(() => {
    if (!ready) return;
    const layer = layers.current.observations;
    layer.removeAll();
    if (!options.observations || !observations) return;
    observations.forEach((f: any) => {
      const fieldId = f.properties?.field_id;
      layer.addFootprints(
        featurePolygons(
          f,
          {
            color: "blue",
            lineWidth: 1,
            fill: true,
            fillColor: selectedObservations.includes(fieldId) ? "red" : "white",
            opacity: 0.6,
          },
          `obs:${fieldId}`,
        ),
      );
    });
  }, [ready, observations, options.observations, selectedObservations]);

  useEffect(() => {
    if (!ready) return;
    layers.current.sources.removeAll();
    if (options.sources && sources?.features) {
      layers.current.sources.addSources(toCatalogSources(sources));
    }
  }, [ready, sources, options.sources]);

  useEffect(() => {
    if (!ready) return;
    layers.current.galaxies.removeAll();
    if (options.galaxies && galaxies?.features) {
      layers.current.galaxies.addSources(toCatalogSources(galaxies));
    }
  }, [ready, galaxies, options.galaxies]);

  useEffect(() => {
    if (!ready) return;
    const { sunMoon, sunExclusion } = layers.current;
    sunMoon.removeAll();
    sunExclusion[options.sun_moon ? "show" : "hide"]();
    if (!options.sun_moon) return;
    const sun = sunPosition(new Date());
    const { ra, dec, fraction, angle } = moonPosition(new Date());
    sunMoon.addSources([
      A.source(sun.ra, sun.dec, { name: "Sun", body: "sun" }),
      A.source(ra, dec, {
        name: `Moon (${Math.round(fraction * 100)}%)`,
        body: "moon",
        fraction,
        angle,
      }),
    ]);
  }, [ready, options.sun_moon]);

  useEffect(() => {
    if (!ready) return;
    const { galacticPlane } = layers.current;
    galacticPlane.removeAll();
    if (!options.galactic_plane) return;
    [-10, 0, 10].forEach((b) =>
      galacticPlane.addFootprints(
        A.polyline(
          Array.from({ length: 361 }, (_, l) => galacticToEquatorial(l, b)),
          b === 0 ? { lineWidth: 2 } : { lineWidth: 1, opacity: 0.5 },
        ),
      ),
    );
  }, [ready, options.galactic_plane]);

  if (!supported) {
    return (
      <Typography variant="body2" color="textSecondary">
        This sky view requires WebGL2, which is not available in this browser.
      </Typography>
    );
  }

  return (
    <Box
      ref={containerRef}
      sx={{
        width: "100%",
        maxWidth: width,
        maxHeight: height,
        aspectRatio: "1 / 1",
      }}
    />
  );
};

const LocalizationPlot = (props: LocalizationPlotProps) =>
  props.localization?.contour ? (
    <AladinGlobe {...props} />
  ) : (
    <CircularProgress />
  );

export default LocalizationPlot;
