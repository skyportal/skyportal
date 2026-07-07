import { useMemo, useState } from "react";
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
import CircularProgress from "@mui/material/CircularProgress";
import Box from "@mui/material/Box";

import createPlotlyComponent from "react-plotly.js/factory";
import Plotly from "./plot/plotlyScatter3d";
import ClassificationSelect from "./classification/ClassificationSelect";
import {
  useGetPhotStatAggregateQuery,
  type PhotStatAggregateArgs,
  type PhotStatPoint,
} from "../ducks/photStatAggregate";

const Plot = createPlotlyComponent(Plotly);

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
    maxHeight: "16rem",
    overflowY: "auto",
  },
  selectedList: {
    display: "flex",
    flexWrap: "wrap",
    gap: "0.5rem",
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

  const handlePlot = () => {
    setSelectedIds([]);
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
          {data.count === 0 ? (
            <Typography>No sources match the current selection.</Typography>
          ) : (
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
