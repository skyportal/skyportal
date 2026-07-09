import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { makeStyles } from "tss-react/mui";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";
import Slider from "@mui/material/Slider";
import Button from "@mui/material/Button";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import CircularProgress from "@mui/material/CircularProgress";
import Box from "@mui/material/Box";

import createPlotlyComponent from "react-plotly.js/factory";
import Plotly from "./plot/plotlyScatter3d";
import ClassificationSelect from "./classification/ClassificationSelect";
import VegaPhotometry from "./plot/VegaPhotometry";
import { useGetSourcePhotometryMinimalQuery } from "../ducks/photometry_minimal";
import {
  useGetPhotStatAggregateQuery,
  type PhotStatAggregateArgs,
  type PhotStatPoint,
} from "../ducks/photStatAggregate";

const Plot = createPlotlyComponent(Plotly);

// Cap how many light curves render at once to keep the page responsive.
const MAX_LIGHT_CURVES = 12;
// Overlaying many curves is cheaper than many separate plots, so allow more.
const MAX_OVERLAY = 40;

// Invisible child: fetches one source's photometry and hands it up. One per
// source lets us use the RTK Query hook (a fixed number per render) and share
// the same cache the source page uses.
const PhotometryFetcher = ({
  sourceId,
  onData,
}: {
  sourceId: string;
  onData: (id: string, data: any[]) => void;
}) => {
  const { data } = useGetSourcePhotometryMinimalQuery(sourceId);
  useEffect(() => {
    if (data) onData(sourceId, data);
  }, [data, sourceId, onData]);
  return null;
};

// Overlay every source's detections on one magnitude-vs-time axis, colored by
// source. `alignPeak` shifts each curve so its brightest point sits at t=0,
// which lines the transients up for shape comparison.
const LightCurveOverlay = ({
  sourceIds,
  alignPeak,
  filterBand,
  onAvailableBands,
}: {
  sourceIds: string[];
  alignPeak: boolean;
  filterBand: string;
  onAvailableBands: (bands: string[]) => void;
}) => {
  const [photMap, setPhotMap] = useState<Record<string, any[]>>({});
  const handleData = useCallback((id: string, data: any[]) => {
    setPhotMap((prev) => (prev[id] === data ? prev : { ...prev, [id]: data }));
  }, []);

  // Report the bands present so the parent can populate the band dropdown.
  const availableBands = useMemo(() => {
    const bands = new Set<string>();
    sourceIds.forEach((id) =>
      (photMap[id] ?? []).forEach((p) => p.filter && bands.add(p.filter)),
    );
    return Array.from(bands).sort();
  }, [photMap, sourceIds]);
  useEffect(() => {
    onAvailableBands(availableBands);
  }, [availableBands, onAvailableBands]);

  const traces = useMemo(
    () =>
      sourceIds
        .map((id) => {
          const pts = (photMap[id] ?? []).filter(
            (p) =>
              p.mag !== null &&
              p.mag !== undefined &&
              (filterBand === "all" || p.filter === filterBand),
          );
          if (!pts.length) return null;
          let t0 = 0;
          if (alignPeak) {
            t0 = pts.reduce((a, b) => (b.mag < a.mag ? b : a)).mjd;
          }
          return {
            type: "scattergl",
            mode: "markers",
            name: id,
            x: pts.map((p) => p.mjd - t0),
            y: pts.map((p) => p.mag),
            text: pts.map((p) => `${id} (${p.filter})`),
            hovertemplate: "%{text}<br>%{x}<br>%{y} mag<extra></extra>",
            marker: { size: 5, opacity: 0.7 },
          };
        })
        .filter(Boolean),
    [photMap, sourceIds, alignPeak],
  );

  const layout = {
    autosize: true,
    height: 650,
    margin: { l: 60, r: 20, t: 10, b: 50 },
    xaxis: { title: { text: alignPeak ? "Days from peak" : "MJD" } },
    yaxis: { title: { text: "Magnitude" }, autorange: "reversed" },
    legend: { orientation: "v" },
  };

  return (
    <>
      {sourceIds.map((id) => (
        <PhotometryFetcher key={id} sourceId={id} onData={handleData} />
      ))}
      <Plot
        data={traces as any}
        layout={layout as any}
        useResizeHandler
        style={{ width: "100%" }}
        config={{ displaylogo: false, responsive: true } as any}
      />
    </>
  );
};

// Fields where a brighter object means a smaller number, so the axis reads
// naturally (bright at top/right) when reversed.
const MAGNITUDE_FIELDS = new Set([
  "first_detected_mag",
  "last_detected_mag",
  "peak_mag_global",
  "mean_mag_global",
  "faintest_mag_global",
  "deepest_limit_global",
]);

const useStyles = makeStyles()((theme) => ({
  root: {
    display: "flex",
    flexDirection: "column",
    gap: "1rem",
    padding: "1rem",
  },
  controls: {
    display: "flex",
    flexWrap: "wrap",
    alignItems: "flex-end",
    gap: "1rem",
    padding: "1rem",
  },
  control: {
    minWidth: "12rem",
  },
  slider: {
    minWidth: "12rem",
    display: "flex",
    flexDirection: "column",
  },
  plotPaper: {
    padding: "0.5rem",
  },
  selected: {
    padding: "1rem",
  },
  selectedList: {
    display: "flex",
    flexWrap: "wrap",
    gap: "0.5rem",
    maxHeight: "8rem",
    overflowY: "auto",
  },
  lcGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(24rem, 1fr))",
    gap: "0.75rem",
    marginTop: "0.75rem",
  },
  lcCard: {
    padding: "0.5rem",
    display: "flex",
    flexDirection: "column",
    gap: "0.25rem",
  },
  warning: {
    color: theme.palette.warning.main,
  },
}));

const SourceStatistics = () => {
  const { classes } = useStyles();
  const navigate = useNavigate();

  const [selectedClassifications, setSelectedClassifications] = useState<
    string[]
  >([]);
  const [xField, setXField] = useState("rise_rate");
  const [yField, setYField] = useState("peak_mag_global");
  const [zField, setZField] = useState("");
  const [probThreshold, setProbThreshold] = useState(0);
  const [xLog, setXLog] = useState(false);
  const [yLog, setYLog] = useState(false);
  const [queryArgs, setQueryArgs] = useState<PhotStatAggregateArgs | null>(
    null,
  );
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [viewMode, setViewMode] = useState<"stats" | "lightcurves" | "overlay">(
    "stats",
  );
  const [lcPage, setLcPage] = useState(0);
  const [alignPeak, setAlignPeak] = useState(false);
  const [overlayBand, setOverlayBand] = useState("all");
  const [overlayBands, setOverlayBands] = useState<string[]>([]);
  const handleAvailableBands = useCallback((bands: string[]) => {
    setOverlayBands((prev) =>
      prev.length === bands.length && prev.every((b, i) => b === bands[i])
        ? prev
        : bands,
    );
  }, []);

  // Metadata request (no axes) fetches the plottable field list.
  const { data: meta } = useGetPhotStatAggregateQuery({});
  const fields = useMemo(() => meta?.fields ?? [], [meta]);
  const labelFor = useMemo(() => {
    const map: Record<string, string> = {};
    fields.forEach((f) => {
      map[f.value] = f.label;
    });
    return map;
  }, [fields]);

  const { data, isFetching } = useGetPhotStatAggregateQuery(queryArgs ?? {}, {
    skip: !queryArgs,
  });

  const is3d = Boolean(queryArgs?.zField);

  // Sources whose light curves to show: the box-selection if any, else every
  // plotted source (capped in the render).
  const plottedIds = useMemo(
    () => (data?.points ?? []).map((p) => p.id),
    [data],
  );
  const lcSourceIds = selectedIds.length > 0 ? selectedIds : plottedIds;

  const handlePlot = () => {
    setSelectedIds([]);
    setLcPage(0);
    setQueryArgs({
      xField,
      yField,
      ...(zField ? { zField } : {}),
      ...(selectedClassifications.length
        ? { classifications: selectedClassifications.join(",") }
        : {}),
      ...(probThreshold > 0
        ? { classificationProbThreshold: probThreshold }
        : {}),
    });
  };

  const traces = useMemo(() => {
    if (!data?.points?.length || !queryArgs) return [];
    const groups = new Map<string, PhotStatPoint[]>();
    data.points.forEach((p) => {
      const key = p.classification ?? "Unclassified";
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key)?.push(p);
    });
    const xLabel = labelFor[queryArgs.xField ?? ""] ?? queryArgs.xField;
    const yLabel = labelFor[queryArgs.yField ?? ""] ?? queryArgs.yField;
    const zLabel = labelFor[queryArgs.zField ?? ""] ?? queryArgs.zField;
    return Array.from(groups.entries()).map(([name, pts]) => ({
      type: is3d ? "scatter3d" : "scattergl",
      mode: "markers",
      name,
      x: pts.map((p) => p.x),
      y: pts.map((p) => p.y),
      ...(is3d ? { z: pts.map((p) => p.z) } : {}),
      customdata: pts.map((p) => p.id),
      text: pts.map((p) => p.id),
      hovertemplate: `%{text}<br>${xLabel}: %{x}<br>${yLabel}: %{y}${
        is3d ? `<br>${zLabel}: %{z}` : ""
      }<extra>${name}</extra>`,
      marker: { size: is3d ? 3 : 5, opacity: 0.65 },
    }));
  }, [data, queryArgs, is3d, labelFor]);

  const layout = useMemo(() => {
    if (!queryArgs) return {};
    const xLabel = labelFor[queryArgs.xField ?? ""] ?? queryArgs.xField;
    const yLabel = labelFor[queryArgs.yField ?? ""] ?? queryArgs.yField;
    const zLabel = labelFor[queryArgs.zField ?? ""] ?? queryArgs.zField;
    const axis = (field: string | undefined, label: any, log: boolean) => ({
      title: { text: label },
      ...(log ? { type: "log" } : {}),
      ...(field && MAGNITUDE_FIELDS.has(field)
        ? { autorange: "reversed" }
        : {}),
    });
    if (is3d) {
      return {
        autosize: true,
        height: 650,
        margin: { l: 0, r: 0, t: 10, b: 0 },
        scene: {
          xaxis: axis(queryArgs.xField, xLabel, false),
          yaxis: axis(queryArgs.yField, yLabel, false),
          zaxis: axis(queryArgs.zField, zLabel, false),
        },
      };
    }
    return {
      autosize: true,
      height: 650,
      margin: { l: 60, r: 20, t: 10, b: 50 },
      dragmode: "select",
      xaxis: axis(queryArgs.xField, xLabel, xLog),
      yaxis: axis(queryArgs.yField, yLabel, yLog),
      legend: { orientation: "v" },
    };
  }, [queryArgs, is3d, xLog, yLog, labelFor]);

  const handleClick = (event: any) => {
    const id = event?.points?.[0]?.customdata;
    if (id) navigate(`/source/${id}`);
  };

  const handleSelected = (event: any) => {
    const ids: string[] = (event?.points ?? [])
      .map((p: any) => p.customdata)
      .filter(Boolean);
    setSelectedIds(Array.from(new Set(ids)));
    setLcPage(0);
  };

  const axisSelect = (
    label: string,
    value: string,
    onChange: (v: string) => void,
    includeNone = false,
  ) => (
    <FormControl className={classes.control} size="small">
      <InputLabel>{label}</InputLabel>
      <Select
        label={label}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        {includeNone && (
          <MenuItem value="">
            <em>None (2D)</em>
          </MenuItem>
        )}
        {fields.map((f) => (
          <MenuItem key={f.value} value={f.value}>
            {f.label}
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );

  return (
    <div className={classes.root}>
      <Typography variant="h4">Source Statistics</Typography>
      <Typography variant="body2" color="textSecondary">
        Plot photometry statistics across many sources at once to spot outliers.
        Optionally down-select by classification; points are colored by each
        source&apos;s highest-probability classification. Click any point to
        open that source. In 2D, drag a box (or use the lasso/box tools in the
        plot toolbar) to list a group of outliers below; the 3D view supports
        rotate and zoom only.
      </Typography>

      <Paper className={classes.controls}>
        <Box className={classes.control}>
          <ClassificationSelect
            selectedClassifications={selectedClassifications}
            setSelectedClassifications={setSelectedClassifications}
          />
        </Box>
        {axisSelect("X axis", xField, setXField)}
        {axisSelect("Y axis", yField, setYField)}
        {axisSelect("Z axis", zField, setZField, true)}
        <Box className={classes.slider}>
          <Typography variant="caption">
            Min. classification probability: {probThreshold.toFixed(2)}
          </Typography>
          <Slider
            value={probThreshold}
            onChange={(_e, v) => setProbThreshold(v as number)}
            min={0}
            max={1}
            step={0.05}
            valueLabelDisplay="auto"
          />
        </Box>
        {!is3d && (
          <Box>
            <FormControlLabel
              control={
                <Switch
                  checked={xLog}
                  onChange={(e) => setXLog(e.target.checked)}
                  size="small"
                />
              }
              label="log X"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={yLog}
                  onChange={(e) => setYLog(e.target.checked)}
                  size="small"
                />
              }
              label="log Y"
            />
          </Box>
        )}
        <Button
          variant="contained"
          onClick={handlePlot}
          disabled={!xField || !yField}
        >
          Plot
        </Button>
      </Paper>

      {isFetching && <CircularProgress />}

      {data && queryArgs && !isFetching && (
        <>
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              flexWrap: "wrap",
              gap: "0.5rem",
            }}
          >
            <Typography variant="body2">
              Showing {data.count.toLocaleString()} source
              {data.count === 1 ? "" : "s"}.
              {data.truncated && (
                <span className={classes.warning}>
                  {" "}
                  Result truncated — narrow the selection to see all matches.
                </span>
              )}
            </Typography>
            {data.count > 0 && (
              <ToggleButtonGroup
                size="small"
                exclusive
                value={viewMode}
                onChange={(_e, v) => v && setViewMode(v)}
              >
                <ToggleButton value="stats">Statistics</ToggleButton>
                <ToggleButton value="lightcurves">Light curves</ToggleButton>
                <ToggleButton value="overlay">Overlay</ToggleButton>
              </ToggleButtonGroup>
            )}
          </Box>

          {data.count === 0 ? (
            <Typography>No sources match the current selection.</Typography>
          ) : viewMode === "stats" ? (
            <Paper className={classes.plotPaper}>
              <Plot
                data={traces as any}
                layout={layout as any}
                useResizeHandler
                style={{ width: "100%" }}
                onClick={handleClick}
                onSelected={handleSelected}
                config={{ displaylogo: false, responsive: true } as any}
              />
            </Paper>
          ) : viewMode === "lightcurves" ? (
            (() => {
              const pageCount = Math.max(
                1,
                Math.ceil(lcSourceIds.length / MAX_LIGHT_CURVES),
              );
              const page = Math.min(lcPage, pageCount - 1);
              const start = page * MAX_LIGHT_CURVES;
              const pageIds = lcSourceIds.slice(
                start,
                start + MAX_LIGHT_CURVES,
              );
              return (
                <Paper className={classes.selected}>
                  <Box
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      flexWrap: "wrap",
                      gap: "0.5rem",
                    }}
                  >
                    <Typography variant="body2" color="textSecondary">
                      {selectedIds.length > 0
                        ? "Light curves for selected sources. "
                        : "Light curves for all plotted sources (box-select in Statistics to focus). "}
                      Showing {start + 1}
                      {"–"}
                      {start + pageIds.length} of {lcSourceIds.length}.
                    </Typography>
                    {pageCount > 1 && (
                      <Box
                        sx={{ display: "flex", alignItems: "center", gap: 1 }}
                      >
                        <Button
                          size="small"
                          disabled={page === 0}
                          onClick={() => setLcPage(page - 1)}
                        >
                          Previous
                        </Button>
                        <Typography variant="body2">
                          {page + 1} / {pageCount}
                        </Typography>
                        <Button
                          size="small"
                          disabled={page >= pageCount - 1}
                          onClick={() => setLcPage(page + 1)}
                        >
                          Next
                        </Button>
                      </Box>
                    )}
                  </Box>
                  <div className={classes.lcGrid}>
                    {pageIds.map((id) => (
                      <Paper
                        key={id}
                        variant="outlined"
                        className={classes.lcCard}
                      >
                        <Link to={`/source/${id}`}>{id}</Link>
                        <VegaPhotometry sourceId={id} />
                      </Paper>
                    ))}
                  </div>
                </Paper>
              );
            })()
          ) : (
            <Paper className={classes.selected}>
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  flexWrap: "wrap",
                  gap: "0.5rem",
                }}
              >
                <Typography variant="body2" color="textSecondary">
                  {selectedIds.length > 0
                    ? "Overlaid light curves for selected sources"
                    : "Overlaid light curves for all plotted sources (box-select in Statistics to focus)"}
                  {lcSourceIds.length > MAX_OVERLAY &&
                    ` — first ${MAX_OVERLAY} of ${lcSourceIds.length}`}
                  , colored by source.
                </Typography>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                  <FormControl size="small" sx={{ minWidth: "8rem" }}>
                    <InputLabel>Band</InputLabel>
                    <Select
                      label="Band"
                      value={overlayBand}
                      onChange={(e) => setOverlayBand(e.target.value)}
                    >
                      <MenuItem value="all">All bands</MenuItem>
                      {overlayBands.map((b) => (
                        <MenuItem key={b} value={b}>
                          {b}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={alignPeak}
                        onChange={(e) => setAlignPeak(e.target.checked)}
                        size="small"
                      />
                    }
                    label="Align to peak"
                  />
                </Box>
              </Box>
              <LightCurveOverlay
                sourceIds={lcSourceIds.slice(0, MAX_OVERLAY)}
                alignPeak={alignPeak}
                filterBand={overlayBand}
                onAvailableBands={handleAvailableBands}
              />
            </Paper>
          )}
        </>
      )}

      {selectedIds.length > 0 && (
        <Paper className={classes.selected}>
          <Typography variant="subtitle1">
            Selected sources ({selectedIds.length})
          </Typography>
          <div className={classes.selectedList}>
            {selectedIds.map((id) => (
              <Link key={id} to={`/source/${id}`}>
                {id}
              </Link>
            ))}
          </div>
        </Paper>
      )}
    </div>
  );
};

export default SourceStatistics;
