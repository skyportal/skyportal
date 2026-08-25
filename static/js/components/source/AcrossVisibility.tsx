import { useMemo, useState } from "react";
import Plotly from "plotly.js-basic-dist";
import createPlotlyComponent from "react-plotly.js/factory";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import TextField from "@mui/material/TextField";
import CircularProgress from "@mui/material/CircularProgress";
import { makeStyles } from "tss-react/mui";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import {
  useGetAcrossJointVisibilityQuery,
  type AcrossSingleVisibility,
  type AcrossVisibilityWindow,
} from "../../ducks/across";

dayjs.extend(utc);

const Plot = createPlotlyComponent(Plotly);

const JOINT_ROW = "JOINT (all selected)";
const MAX_TELESCOPES = 8;

const useStyles = makeStyles()({
  container: {
    margin: "1rem 0",
    padding: "1rem",
  },
  controls: {
    display: "flex",
    flexWrap: "wrap",
    gap: "1rem",
    alignItems: "center",
    marginBottom: "1rem",
  },
});

// datetime-local wants "YYYY-MM-DDTHH:mm"; the API wants full ISO (UTC).
const toApiTime = (local: string) =>
  dayjs.utc(local).format("YYYY-MM-DDTHH:mm:ss");

interface AcrossVisibilityProps {
  objId: string;
  telescopes: { id: number; name: string }[];
}

const AcrossVisibility = ({ objId, telescopes }: AcrossVisibilityProps) => {
  const { classes } = useStyles();
  const [begin, setBegin] = useState(dayjs.utc().format("YYYY-MM-DDTHH:mm"));
  const [end, setEnd] = useState(
    dayjs.utc().add(3, "day").format("YYYY-MM-DDTHH:mm"),
  );

  const capped = telescopes.slice(0, MAX_TELESCOPES);
  const telescopeIds = capped.map((t) => t.id);

  // Auto-compute whenever the selection or date range changes.
  const { data, isFetching, error } = useGetAcrossJointVisibilityQuery(
    {
      objId,
      telescopeIds,
      begin: toApiTime(begin),
      end: toApiTime(end),
    },
    { skip: telescopeIds.length < 1 },
  );

  const plotData = useMemo(() => {
    if (!data) return [];
    const traces: Record<string, unknown>[] = [];
    const addWindows = (
      windows: AcrossVisibilityWindow[],
      row: string,
      color: string,
    ) => {
      windows.forEach((w, i) => {
        traces.push({
          x: [w.begin, w.end],
          y: [row, row],
          type: "scatter",
          mode: "lines",
          line: { color, width: 16 },
          showlegend: false,
          hovertemplate: `${row}<br>%{x}<extra>${w.duration_hr.toFixed(2)} hr</extra>`,
          name: `${row}-${i}`,
        });
      });
    };
    // ground = blue, space = green, joint = orange
    addWindows(data.joint, JOINT_ROW, "#e8590c");
    data.single.forEach((s) =>
      addWindows(s.windows, s.name, s.kind === "space" ? "#2f9e44" : "#1f77b4"),
    );
    return traces;
  }, [data]);

  const yOrder = useMemo(() => {
    if (!data) return [];
    // Plotly draws the first category at the bottom; joint sits on top.
    return [...data.single.map((s) => s.name), JOINT_ROW];
  }, [data]);

  const perTelescopeErrors = (data?.single || []).filter(
    (s: AcrossSingleVisibility) => s.error,
  );

  return (
    <Paper className={classes.container}>
      <Typography variant="h6" gutterBottom>
        Joint visibility
      </Typography>
      <Typography variant="body2" color="textSecondary" gutterBottom>
        Per-facility visibility for the selected telescopes &mdash; ground
        (blue, source below airmass {data?.ground_max_airmass ?? 2.9} at night,
        matching the airmass plots below) and NASA ACROSS space instruments
        (green) &mdash; plus the joint windows (orange) when every selected
        facility can observe the source simultaneously.
        {telescopes.length > MAX_TELESCOPES &&
          ` Showing the first ${MAX_TELESCOPES} of ${telescopes.length} selected.`}
      </Typography>

      {telescopeIds.length < 1 ? (
        <Typography variant="body2" style={{ marginTop: "0.5rem" }}>
          Select telescopes in the Observability preferences above to see their
          visibility.
        </Typography>
      ) : (
        <>
          <div className={classes.controls}>
            <TextField
              label="Begin (UTC)"
              type="datetime-local"
              size="small"
              value={begin}
              onChange={(e) => setBegin(e.target.value)}
              slotProps={{ inputLabel: { shrink: true } }}
            />
            <TextField
              label="End (UTC)"
              type="datetime-local"
              size="small"
              value={end}
              onChange={(e) => setEnd(e.target.value)}
              slotProps={{ inputLabel: { shrink: true } }}
            />
            {isFetching && <CircularProgress size={24} color="secondary" />}
          </div>

          {error && (
            <Typography variant="body2" color="error">
              {(error as any)?.data?.message || "Failed to compute visibility."}
            </Typography>
          )}

          {perTelescopeErrors.length > 0 && (
            <Typography variant="body2" color="error" gutterBottom>
              Some facilities failed:{" "}
              {perTelescopeErrors.map((s) => s.name).join(", ")} (the ACROSS
              calculator may have timed out; try a shorter window).
            </Typography>
          )}

          {data && !isFetching && (
            <Plot
              data={plotData as any}
              layout={
                {
                  height: 120 + 40 * (yOrder.length || 1),
                  margin: { l: 220, r: 20, t: 10, b: 40 },
                  xaxis: { title: "UTC time", type: "date" },
                  yaxis: {
                    type: "category",
                    categoryorder: "array",
                    categoryarray: yOrder,
                    automargin: true,
                  },
                } as any
              }
              config={{ displayModeBar: false, responsive: true } as any}
              style={{ width: "100%" }}
            />
          )}
        </>
      )}
    </Paper>
  );
};

export default AcrossVisibility;
