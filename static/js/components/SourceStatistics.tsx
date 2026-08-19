import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { makeStyles } from "tss-react/mui";
import { Link, useNavigate } from "react-router-dom";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";
import Slider from "@mui/material/Slider";
import Button from "./Button";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import CircularProgress from "@mui/material/CircularProgress";
import Box from "@mui/material/Box";
import Autocomplete from "@mui/material/Autocomplete";
import TextField from "@mui/material/TextField";

import createPlotlyComponent from "react-plotly.js/factory";
import Plotly from "./plot/plotlyScatter3d";
import ClassificationSelect from "./classification/ClassificationSelect";
import VegaPhotometry from "./plot/VegaPhotometry";
import SpectraAggregation from "./SpectraAggregation";
import { useGetGroupsQuery } from "../ducks/groups";
import { useGetSourcePhotometryOverlayQuery } from "../ducks/photometry_minimal";
import { smoothing_func } from "../utils";
import { GET } from "../API";
import { useAppDispatch } from "../types/hooks";
import useDebounced from "../hooks/useDebounced";
import {
  useGetPhotStatAggregateQuery,
  type PhotStatAggregateArgs,
  type PhotStatPoint,
} from "../ducks/photStatAggregate";

const Plot = createPlotlyComponent(Plotly);

const SourceIdAutocomplete = ({
  value,
  onChange,
  sx,
}: {
  value: string[];
  onChange: (ids: string[]) => void;
  sx?: object;
}) => {
  const dispatch = useAppDispatch();
  const [options, setOptions] = useState<string[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [loading, setLoading] = useState(false);
  const debounced = useDebounced(inputValue, 400);
  const labels = useRef<Record<string, string>>({});
  const cache = useRef<Record<string, string[]>>({});

  useEffect(() => {
    const cached = cache.current[debounced];
    if (!debounced || cached) {
      setOptions(cached ?? []);
      return undefined;
    }
    let active = true;
    setLoading(true);
    (async () => {
      const resp: any = await dispatch(
        GET(
          `/api/sources?sourceID=${encodeURIComponent(debounced)}&pageNumber=1&numPerPage=25&totalMatches=25&includeComments=false&removeNested=true`,
          "skyportal/FETCH_SOURCE_ID_AUTOCOMPLETE",
        ),
      );
      if (!active) return;
      const ids = (resp?.data?.sources ?? []).map((source: any) => {
        labels.current[source.id] = source.tns_name
          ? `${source.id} (${source.tns_name})`
          : source.id;
        return source.id;
      });
      cache.current[debounced] = ids;
      setOptions(ids);
      setLoading(false);
    })();
    return () => {
      active = false;
      setLoading(false);
    };
  }, [debounced, dispatch]);

  return (
    <Autocomplete
      multiple
      freeSolo
      size="small"
      sx={sx}
      options={options}
      loading={loading}
      value={value}
      inputValue={inputValue}
      onInputChange={(_e, input) => setInputValue(input)}
      filterOptions={(opts) => opts}
      filterSelectedOptions
      renderOption={(props, option) => (
        <li {...props} key={option}>
          {labels.current[option] ?? option}
        </li>
      )}
      onChange={(_e, values) => {
        const ids = (values as string[]).flatMap((entry) =>
          entry.split(/[\s,]+/),
        );
        onChange(Array.from(new Set(ids.filter(Boolean))));
        setInputValue("");
      }}
      renderInput={(params) => (
        <TextField
          {...params}
          label="Object IDs"
          placeholder="Type to search sources…"
        />
      )}
    />
  );
};

const MAX_LIGHT_CURVES = 12;
const MAX_OVERLAY = 40;

const PhotometryFetcher = ({
  sourceId,
  includeExtinction,
  onData,
}: {
  sourceId: string;
  includeExtinction: boolean;
  onData: (id: string, data: any[]) => void;
}) => {
  const { data } = useGetSourcePhotometryOverlayQuery({
    id: sourceId,
    includeExtinction,
  });
  useEffect(() => {
    if (data) onData(sourceId, data);
  }, [data, sourceId, onData]);
  return null;
};

// Planck18 FlatLambdaCDM
const H0 = 67.66;
const OM = 0.30966;
const OL = 1 - OM;
const C_KM_S = 299792.458;
const distanceModulus = (z: number | null): number | null => {
  if (!z || z <= 0) return null;
  const invE = (zp: number) => 1 / Math.sqrt(OM * (1 + zp) ** 3 + OL);
  const n = 200;
  const h = z / n;
  let s = invE(0) + invE(z);
  for (let i = 1; i < n; i += 1) s += (i % 2 === 0 ? 2 : 4) * invE(i * h);
  const dcMpc = (C_KM_S / H0) * (h / 3) * s; // comoving distance
  const dlPc = (1 + z) * dcMpc * 1e6; // luminosity distance in pc
  return 5 * Math.log10(dlPc / 10);
};

const interpMag = (pts: any[], mjd: number): number | null => {
  if (!pts.length || mjd < pts[0].mjd || mjd > pts[pts.length - 1].mjd)
    return null;
  for (let i = 1; i < pts.length; i += 1) {
    if (pts[i].mjd >= mjd) {
      const a = pts[i - 1];
      const b = pts[i];
      if (b.mjd === a.mjd) return b.mag;
      return a.mag + ((mjd - a.mjd) / (b.mjd - a.mjd)) * (b.mag - a.mag);
    }
  }
  return null;
};

type AlignMode = "none" | "peak" | "first";

const alignT0 = (sortedPts: any[], alignMode: AlignMode) => {
  if (!sortedPts.length) return 0;
  if (alignMode === "first") return sortedPts[0].mjd;
  if (alignMode === "peak")
    return sortedPts.reduce((a, b) => (b.mag < a.mag ? b : a)).mjd;
  return 0;
};

const alignAxisLabel = (alignMode: AlignMode) =>
  alignMode === "peak"
    ? "Days from peak"
    : alignMode === "first"
      ? "Days from first detection"
      : "MJD";

const LightCurveOverlay = ({
  sourceIds,
  alignMode,
  smoothWindow,
  mode,
  filterBand,
  colorPair,
  absolute,
  extinction,
  dmMap,
  onAvailableBands,
}: {
  sourceIds: string[];
  alignMode: AlignMode;
  smoothWindow: number;
  mode: "mag" | "color";
  filterBand: string;
  colorPair: string;
  absolute: boolean;
  extinction: boolean;
  dmMap: Record<string, number>;
  onAvailableBands: (bands: string[]) => void;
}) => {
  const [photMap, setPhotMap] = useState<Record<string, any[]>>({});
  const handleData = useCallback((id: string, data: any[]) => {
    setPhotMap((prev) => (prev[id] === data ? prev : { ...prev, [id]: data }));
  }, []);

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

  const traces = useMemo(() => {
    const smooth = smoothWindow > 0;
    const detections = (id: string) =>
      (photMap[id] ?? [])
        .map((p) => ({
          mjd: p.mjd,
          filter: p.filter,
          mag: extinction ? p.mag_corr : p.mag,
        }))
        .filter((p) => p.mag !== null && p.mag !== undefined);

    if (mode === "color") {
      const [b1, b2] = colorPair.split("-");
      return sourceIds
        .map((id) => {
          const pts = detections(id);
          const p1 = pts
            .filter((p) => p.filter === b1)
            .sort((a, b) => a.mjd - b.mjd);
          const p2 = pts
            .filter((p) => p.filter === b2)
            .sort((a, b) => a.mjd - b.mjd);
          if (p1.length < 1 || p2.length < 2) return null;
          const t0 = alignT0(p1, alignMode);
          const xs: number[] = [];
          let ys: number[] = [];
          p1.forEach((pt) => {
            const m2 = interpMag(p2, pt.mjd);
            if (m2 !== null) {
              xs.push(pt.mjd - t0);
              ys.push(pt.mag - m2);
            }
          });
          if (!xs.length) return null;
          if (smooth) ys = smoothing_func(ys, smoothWindow) ?? ys;
          return {
            type: "scattergl",
            mode: smooth ? "lines" : "lines+markers",
            name: id,
            x: xs,
            y: ys,
            hovertemplate: `${id}<br>%{x}<br>${colorPair}: %{y:.2f}<extra></extra>`,
            marker: { size: 5, opacity: 0.7 },
          };
        })
        .filter(Boolean);
    }

    return sourceIds
      .map((id) => {
        const pts = detections(id)
          .filter((p) => filterBand === "all" || p.filter === filterBand)
          .sort((a, b) => a.mjd - b.mjd);
        if (!pts.length) return null;
        const dm = dmMap[id];
        if (absolute && dm === undefined) return null; // no redshift
        const offset = absolute && dm !== undefined ? dm : 0;
        const t0 = alignT0(pts, alignMode);
        let ys = pts.map((p) => p.mag - offset);
        if (smooth) ys = smoothing_func(ys, smoothWindow) ?? ys;
        return {
          type: "scattergl",
          mode: smooth ? "lines" : "markers",
          name: id,
          x: pts.map((p) => p.mjd - t0),
          y: ys,
          text: pts.map((p) => `${id} (${p.filter})`),
          hovertemplate: "%{text}<br>%{x}<br>%{y:.2f} mag<extra></extra>",
          marker: { size: 5, opacity: 0.7 },
        };
      })
      .filter(Boolean);
  }, [
    photMap,
    sourceIds,
    alignMode,
    smoothWindow,
    mode,
    filterBand,
    colorPair,
    absolute,
    extinction,
    dmMap,
  ]);

  const yaxis =
    mode === "color"
      ? { title: { text: `${colorPair} (mag)` } }
      : {
          title: { text: absolute ? "Absolute magnitude" : "Magnitude" },
          autorange: "reversed" as const,
        };

  const layout = {
    autosize: true,
    height: 650,
    margin: { l: 60, r: 20, t: 10, b: 50 },
    xaxis: { title: { text: alignAxisLabel(alignMode) } },
    yaxis,
    legend: { orientation: "v" },
  };

  return (
    <>
      {sourceIds.map((id) => (
        <PhotometryFetcher
          key={id}
          sourceId={id}
          includeExtinction={extinction}
          onData={handleData}
        />
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

const MAGNITUDE_FIELDS = new Set([
  "first_detected_mag",
  "last_detected_mag",
  "peak_mag_global",
  "mean_mag_global",
  "faintest_mag_global",
  "deepest_limit_global",
]);

const useStyles = makeStyles()((theme) => ({
  control: {
    minWidth: "12rem",
  },
  headerRow: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    flexWrap: "wrap",
    gap: "0.5rem",
  },
  selected: {
    padding: "1rem",
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
  const [sourceMode, setSourceMode] = useState<
    "classification" | "group" | "objects"
  >("classification");
  const [selectGroupId, setSelectGroupId] = useState<number | "">("");
  const [objIds, setObjIds] = useState<string[]>([]);
  const { data: groupsData } = useGetGroupsQuery();
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
  const [viewMode, setViewMode] = useState<
    "stats" | "lightcurves" | "overlay" | "color" | "spectra"
  >("stats");
  const [lcPage, setLcPage] = useState(0);
  const [alignMode, setAlignMode] = useState<AlignMode>("none");
  const [smoothWindow, setSmoothWindow] = useState(0);
  const [overlayBand, setOverlayBand] = useState("all");
  const [overlayBands, setOverlayBands] = useState<string[]>([]);
  const [absoluteMag, setAbsoluteMag] = useState(false);
  const [extinction, setExtinction] = useState(false);
  const [colorPair, setColorPair] = useState("");
  const handleAvailableBands = useCallback((bands: string[]) => {
    if (bands.length === 0) return;
    setOverlayBands((prev) =>
      prev.length === bands.length && prev.every((b, i) => b === bands[i])
        ? prev
        : bands,
    );
  }, []);

  const colorPairs = useMemo(() => {
    const pairs: string[] = [];
    for (let i = 0; i < overlayBands.length; i += 1)
      for (let j = i + 1; j < overlayBands.length; j += 1)
        pairs.push(`${overlayBands[i]}-${overlayBands[j]}`);
    return pairs;
  }, [overlayBands]);
  useEffect(() => {
    const first = colorPairs[0];
    if (first && !colorPairs.includes(colorPair)) setColorPair(first);
  }, [colorPairs, colorPair]);

  const { data: meta } = useGetPhotStatAggregateQuery({});
  const fields = useMemo(() => meta?.fields ?? [], [meta]);
  const labelOf = useCallback(
    (field?: string) => fields.find((f) => f.value === field)?.label ?? field,
    [fields],
  );

  const { data, isFetching } = useGetPhotStatAggregateQuery(queryArgs ?? {}, {
    skip: !queryArgs,
  });

  const is3d = Boolean(queryArgs?.zField);

  const plottedIds = useMemo(
    () => (data?.points ?? []).map((p) => p.id),
    [data],
  );
  const lcSourceIds = selectedIds.length > 0 ? selectedIds : plottedIds;

  const specPoints = useMemo(
    () =>
      selectedIds.length > 0
        ? (data?.points ?? []).filter((p) => selectedIds.includes(p.id))
        : (data?.points ?? []),
    [data, selectedIds],
  );

  const dmMap = useMemo(() => {
    const m: Record<string, number> = {};
    (data?.points ?? []).forEach((p) => {
      const dm = distanceModulus(p.redshift);
      if (dm !== null) m[p.id] = dm;
    });
    return m;
  }, [data]);

  const handlePlot = () => {
    setSelectedIds([]);
    setLcPage(0);
    setQueryArgs({
      xField,
      yField,
      ...(zField ? { zField } : {}),
      ...(sourceMode === "classification" && selectedClassifications.length
        ? {
            classifications: selectedClassifications.join(","),
            ...(probThreshold > 0
              ? { classificationProbThreshold: probThreshold }
              : {}),
          }
        : {}),
      ...(sourceMode === "group" && selectGroupId !== ""
        ? { group_id: selectGroupId }
        : {}),
      ...(sourceMode === "objects" && objIds.length
        ? { obj_ids: objIds.join(",") }
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
    return Array.from(groups.entries()).map(([name, pts]) => ({
      type: is3d ? "scatter3d" : "scattergl",
      mode: "markers",
      name,
      x: pts.map((p) => p.x),
      y: pts.map((p) => p.y),
      ...(is3d ? { z: pts.map((p) => p.z) } : {}),
      customdata: pts.map((p) => p.id),
      text: pts.map((p) => p.id),
      hovertemplate: `%{text}<br>${labelOf(queryArgs.xField)}: %{x}<br>${labelOf(
        queryArgs.yField,
      )}: %{y}${
        is3d ? `<br>${labelOf(queryArgs.zField)}: %{z}` : ""
      }<extra>${name}</extra>`,
      marker: { size: is3d ? 3 : 5, opacity: 0.65 },
    }));
  }, [data, queryArgs, is3d, labelOf]);

  const layout = useMemo(() => {
    if (!queryArgs) return {};
    const axis = (field: string | undefined, log: boolean) => ({
      title: { text: labelOf(field) },
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
          xaxis: axis(queryArgs.xField, false),
          yaxis: axis(queryArgs.yField, false),
          zaxis: axis(queryArgs.zField, false),
        },
      };
    }
    return {
      autosize: true,
      height: 650,
      margin: { l: 60, r: 20, t: 10, b: 50 },
      dragmode: "select",
      xaxis: axis(queryArgs.xField, xLog),
      yaxis: axis(queryArgs.yField, yLog),
      legend: { orientation: "v" },
    };
  }, [queryArgs, is3d, xLog, yLog, labelOf]);

  const isColorView = viewMode === "color";
  const lcPageCount = Math.max(
    1,
    Math.ceil(lcSourceIds.length / MAX_LIGHT_CURVES),
  );
  const lcCurrentPage = Math.min(lcPage, lcPageCount - 1);
  const lcStart = lcCurrentPage * MAX_LIGHT_CURVES;
  const lcPageIds = lcSourceIds.slice(lcStart, lcStart + MAX_LIGHT_CURVES);

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

  const alignSmoothControls = (
    <>
      <FormControlLabel
        control={
          <Switch
            checked={extinction}
            onChange={(e) => setExtinction(e.target.checked)}
            size="small"
          />
        }
        label="Extinction"
      />
      <ToggleButtonGroup
        size="small"
        exclusive
        value={alignMode}
        onChange={(_e, v) => v && setAlignMode(v)}
      >
        <ToggleButton value="none">MJD</ToggleButton>
        <ToggleButton value="peak">Peak</ToggleButton>
        <ToggleButton value="first">First</ToggleButton>
      </ToggleButtonGroup>
      <Box sx={{ width: "9rem", display: "flex", flexDirection: "column" }}>
        <Typography variant="caption">Smoothing: {smoothWindow}</Typography>
        <Slider
          size="small"
          value={smoothWindow}
          onChange={(_e, v) => setSmoothWindow(v as number)}
          min={0}
          max={20}
          step={1}
          valueLabelDisplay="auto"
        />
      </Box>
    </>
  );

  return (
    <Box
      sx={{ display: "flex", flexDirection: "column", gap: "1rem", p: "1rem" }}
    >
      <Typography variant="h4">Source Statistics</Typography>
      <Typography variant="body2" color="textSecondary">
        Plot photometry statistics across many sources at once to spot outliers.
        Down-select by classification, a group&apos;s sources, or an explicit
        object list; points are colored by each source&apos;s
        highest-probability classification. Click any point to open that source.
        In 2D, drag a box (or use the lasso/box tools in the plot toolbar) to
        list a group of outliers below; the 3D view supports rotate and zoom
        only.
      </Typography>

      <Paper
        sx={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "flex-end",
          gap: "1rem",
          p: "1rem",
        }}
      >
        <ToggleButtonGroup
          size="small"
          exclusive
          value={sourceMode}
          onChange={(_e, v) => v && setSourceMode(v)}
        >
          <ToggleButton value="classification">Classification</ToggleButton>
          <ToggleButton value="group">Group</ToggleButton>
          <ToggleButton value="objects">Object list</ToggleButton>
        </ToggleButtonGroup>
        {sourceMode === "classification" && (
          <Box className={classes.control}>
            <ClassificationSelect
              selectedClassifications={selectedClassifications}
              setSelectedClassifications={setSelectedClassifications}
            />
          </Box>
        )}
        {sourceMode === "group" && (
          <FormControl size="small" className={classes.control}>
            <InputLabel>Group</InputLabel>
            <Select
              label="Group"
              value={selectGroupId}
              onChange={(e) => setSelectGroupId(e.target.value as number)}
            >
              {(groupsData?.userAccessible || []).map((g) => (
                <MenuItem key={g.id} value={g.id}>
                  {g.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        )}
        {sourceMode === "objects" && (
          <SourceIdAutocomplete
            value={objIds}
            onChange={setObjIds}
            sx={{ minWidth: "22rem" }}
          />
        )}
        {axisSelect("X axis", xField, setXField)}
        {axisSelect("Y axis", yField, setYField)}
        {axisSelect("Z axis", zField, setZField, true)}
        {sourceMode === "classification" && (
          <Box
            sx={{ minWidth: "12rem", display: "flex", flexDirection: "column" }}
          >
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
        )}
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
        <Button primary onClick={handlePlot} disabled={!xField || !yField}>
          Plot
        </Button>
      </Paper>

      {isFetching && <CircularProgress />}

      {data && queryArgs && !isFetching && (
        <>
          <Box className={classes.headerRow}>
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
                <ToggleButton value="color">Color</ToggleButton>
                <ToggleButton value="spectra">Spectra</ToggleButton>
              </ToggleButtonGroup>
            )}
          </Box>

          {data.count === 0 && (
            <Typography>No sources match the current selection.</Typography>
          )}

          {data.count > 0 && viewMode === "stats" && (
            <Paper sx={{ p: "0.5rem" }}>
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
          )}

          {data.count > 0 && viewMode === "lightcurves" && (
            <Paper className={classes.selected}>
              <Box className={classes.headerRow}>
                <Typography variant="body2" color="textSecondary">
                  {selectedIds.length > 0
                    ? "Light curves for selected sources. "
                    : "Light curves for all plotted sources (box-select in Statistics to focus). "}
                  Showing {lcStart + 1}
                  {"–"}
                  {lcStart + lcPageIds.length} of {lcSourceIds.length}.
                </Typography>
                {lcPageCount > 1 && (
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <Button
                      size="small"
                      disabled={lcCurrentPage === 0}
                      onClick={() => setLcPage(lcCurrentPage - 1)}
                    >
                      Previous
                    </Button>
                    <Typography variant="body2">
                      {lcCurrentPage + 1} / {lcPageCount}
                    </Typography>
                    <Button
                      size="small"
                      disabled={lcCurrentPage >= lcPageCount - 1}
                      onClick={() => setLcPage(lcCurrentPage + 1)}
                    >
                      Next
                    </Button>
                  </Box>
                )}
              </Box>
              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(24rem, 1fr))",
                  gap: "0.75rem",
                  mt: "0.75rem",
                }}
              >
                {lcPageIds.map((id) => (
                  <Paper
                    key={id}
                    variant="outlined"
                    sx={{
                      p: "0.5rem",
                      display: "flex",
                      flexDirection: "column",
                      gap: "0.25rem",
                    }}
                  >
                    <Link to={`/source/${id}`}>{id}</Link>
                    <VegaPhotometry sourceId={id} />
                  </Paper>
                ))}
              </Box>
            </Paper>
          )}

          {data.count > 0 && viewMode === "spectra" && (
            <SpectraAggregation points={specPoints} />
          )}

          {data.count > 0 &&
            (viewMode === "overlay" || viewMode === "color") && (
              <Paper className={classes.selected}>
                <Box className={classes.headerRow}>
                  <Typography variant="body2" color="textSecondary">
                    {isColorView
                      ? "Color evolution (interpolated to shared epochs)"
                      : selectedIds.length > 0
                        ? "Overlaid light curves for selected sources"
                        : "Overlaid light curves for all plotted sources (box-select in Statistics to focus)"}
                    {lcSourceIds.length > MAX_OVERLAY &&
                      ` — first ${MAX_OVERLAY} of ${lcSourceIds.length}`}
                    , colored by source.
                  </Typography>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    {isColorView ? (
                      <FormControl size="small" sx={{ minWidth: "9rem" }}>
                        <InputLabel>Color</InputLabel>
                        <Select
                          label="Color"
                          value={
                            colorPairs.includes(colorPair) ? colorPair : ""
                          }
                          onChange={(e) => setColorPair(e.target.value)}
                        >
                          {colorPairs.map((c) => (
                            <MenuItem key={c} value={c}>
                              {c}
                            </MenuItem>
                          ))}
                        </Select>
                      </FormControl>
                    ) : (
                      <>
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
                              checked={absoluteMag}
                              onChange={(e) => setAbsoluteMag(e.target.checked)}
                              size="small"
                            />
                          }
                          label="Absolute mag"
                        />
                      </>
                    )}
                    {alignSmoothControls}
                  </Box>
                </Box>
                {!isColorView && absoluteMag && (
                  <Typography variant="body2" className={classes.warning}>
                    Absolute magnitude uses each source&apos;s redshift; sources
                    without a redshift are hidden.
                  </Typography>
                )}
                <LightCurveOverlay
                  sourceIds={lcSourceIds.slice(0, MAX_OVERLAY)}
                  alignMode={alignMode}
                  smoothWindow={smoothWindow}
                  mode={isColorView ? "color" : "mag"}
                  filterBand={overlayBand}
                  colorPair={colorPair}
                  absolute={!isColorView && absoluteMag}
                  extinction={extinction}
                  dmMap={dmMap}
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
          <Box
            sx={{
              display: "flex",
              flexWrap: "wrap",
              gap: "0.5rem",
              maxHeight: "8rem",
              overflowY: "auto",
            }}
          >
            {selectedIds.map((id) => (
              <Link key={id} to={`/source/${id}`}>
                {id}
              </Link>
            ))}
          </Box>
        </Paper>
      )}
    </Box>
  );
};

export default SourceStatistics;
