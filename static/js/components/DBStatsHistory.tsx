import { useMemo, useState } from "react";
import { useTheme } from "@mui/material/styles";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import FormControl from "@mui/material/FormControl";
import FormControlLabel from "@mui/material/FormControlLabel";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Switch from "@mui/material/Switch";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Typography from "@mui/material/Typography";

import Plotly from "plotly.js-basic-dist";
import createPlotlyComponent from "react-plotly.js/factory";

import {
  useGetDbStatsHistoryQuery,
  type DBStatsInterval,
} from "../ducks/dbStatsHistory";
import { BASE_LAYOUT, plotAxisTheme, plotCanvasTheme } from "../utils";

const Plot: any = createPlotlyComponent(Plotly);

const HOUR_MS = 3600 * 1000;
const DAY_MS = 24 * HOUR_MS;

const RANGES = [
  { key: "24h", label: "24 hours", ms: DAY_MS },
  { key: "7d", label: "7 days", ms: 7 * DAY_MS },
  { key: "30d", label: "30 days", ms: 30 * DAY_MS },
  { key: "90d", label: "90 days", ms: 90 * DAY_MS },
  { key: "1y", label: "1 year", ms: 365 * DAY_MS },
];

const INTERVALS: { key: DBStatsInterval; label: string; ms: number }[] = [
  { key: "hour", label: "Hourly", ms: HOUR_MS },
  { key: "day", label: "Daily", ms: DAY_MS },
  { key: "week", label: "Weekly", ms: 7 * DAY_MS },
  { key: "month", label: "Monthly", ms: 30 * DAY_MS },
];

const MIN_BINS = 3;
const MAX_BINS = 2000;

const allowedIntervals = (rangeMs: number) =>
  INTERVALS.filter(
    ({ ms }) => rangeMs / ms >= MIN_BINS && rangeMs / ms <= MAX_BINS,
  );

const labelFor = (table: string) => table.replace(/_/g, " ");

const DBStatsHistory = () => {
  const theme = useTheme();
  // A fresh Date.now() per render would change the query key and refetch forever.
  const [now] = useState(() => Date.now());
  const [range, setRange] = useState(RANGES[2]!);
  const [intervalKey, setIntervalKey] = useState<DBStatsInterval>("day");
  const [tables, setTables] = useState<string[]>(["candidates"]);
  const [cumulative, setCumulative] = useState(false);

  const intervals = allowedIntervals(range.ms);
  const interval =
    intervals.find((i) => i.key === intervalKey)?.key ?? intervals[0]!.key;

  const { data, isFetching, isError } = useGetDbStatsHistoryQuery({
    tables: tables.join(","),
    interval,
    startDate: new Date(now - range.ms).toISOString(),
  });

  const traces = useMemo(() => {
    if (!data) return [];
    return tables
      .filter((table) => data.counts[table])
      .map((table) => {
        const counts = data.counts[table]!;
        let running = 0;
        const y = cumulative
          ? counts.map((count) => {
              running += count;
              return running;
            })
          : counts;
        const total = counts.reduce((sum, count) => sum + count, 0);
        return {
          x: data.bins,
          y,
          type: cumulative ? "scatter" : "bar",
          name: `${labelFor(table)} (${total.toLocaleString()})`,
          hovertemplate: `%{y:,} ${labelFor(table)}<extra></extra>`,
        };
      });
  }, [data, tables, cumulative]);

  const axisTheme = plotAxisTheme(theme);

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
      <Typography variant="h6">Rows added per interval</Typography>
      <Box
        sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 2 }}
      >
        <ToggleButtonGroup
          size="small"
          exclusive
          value={range.key}
          onChange={(_e, value) =>
            setRange(RANGES.find((r) => r.key === value) ?? range)
          }
        >
          {RANGES.map((r) => (
            <ToggleButton key={r.key} value={r.key}>
              {r.label}
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
        <ToggleButtonGroup
          size="small"
          exclusive
          value={interval}
          onChange={(_e, value) => value && setIntervalKey(value)}
        >
          {INTERVALS.map((i) => (
            <ToggleButton
              key={i.key}
              value={i.key}
              disabled={!intervals.includes(i)}
            >
              {i.label}
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
        <FormControl size="small" sx={{ minWidth: "16rem" }}>
          <InputLabel id="db-stats-history-tables-label">Tables</InputLabel>
          <Select
            multiple
            labelId="db-stats-history-tables-label"
            id="db-stats-history-tables"
            label="Tables"
            value={tables}
            onChange={(event) => {
              const value = event.target.value as string[];
              if (value.length) setTables(value);
            }}
            renderValue={(selected) => (
              <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
                {(selected as string[]).map((table) => (
                  <Chip key={table} size="small" label={labelFor(table)} />
                ))}
              </Box>
            )}
          >
            {(data?.tables ?? tables).map((table) => (
              <MenuItem key={table} value={table}>
                {labelFor(table)}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <FormControlLabel
          control={
            <Switch
              checked={cumulative}
              onChange={(event) => setCumulative(event.target.checked)}
            />
          }
          label="Cumulative"
        />
        {isFetching && <CircularProgress size="1.5rem" />}
      </Box>
      {isError ? (
        <Typography color="error">Could not load DB history.</Typography>
      ) : (
        <Plot
          data={traces}
          layout={{
            ...plotCanvasTheme(theme),
            height: 400,
            margin: { t: 20, r: 20, b: 60, l: 70 },
            barmode: "group",
            bargap: 0.1,
            hovermode: "x unified",
            showlegend: true,
            legend: { orientation: "h", y: -0.2 },
            xaxis: { ...BASE_LAYOUT, ...axisTheme, type: "date" },
            yaxis: {
              ...BASE_LAYOUT,
              ...axisTheme,
              title: { text: cumulative ? "Cumulative rows" : "Rows added" },
              rangemode: "tozero",
            },
          }}
          config={{ displaylogo: false, responsive: true }}
          style={{ width: "100%" }}
          useResizeHandler
        />
      )}
    </Box>
  );
};

export default DBStatsHistory;
