import { useState } from "react";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Plotly from "plotly.js-basic-dist";
import createPlotlyComponent from "react-plotly.js/factory";

import { useGetFollowupRequestsQuery } from "../../ducks/followup_requests";

const Plot: any = createPlotlyComponent(Plotly);

const HOUR_MS = 3600 * 1000;
const DAY_MS = 24 * HOUR_MS;

const WINDOWS = [
  { key: "1h", label: "1 hour", ms: HOUR_MS },
  { key: "24h", label: "24 hours", ms: DAY_MS },
  { key: "1w", label: "1 week", ms: 7 * DAY_MS },
  { key: "30d", label: "30 days", ms: 30 * DAY_MS },
  { key: "all", label: "Lifetime", ms: Infinity },
];

// status is free text; each bucket matches by substring (the API filters with
// `.contains`). "Other" is whatever doesn't match any bucket.
const COLORS = {
  Completed: "#2e7d32",
  Submitted: "#0288d1",
  Pending: "#ed6c02",
  Failed: "#d32f2f",
  Deleted: "#757575",
  Other: "#bdbdbd",
};

const Tile = ({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color?: string;
}) => (
  <Paper
    variant="outlined"
    style={{ padding: "0.5rem 1rem", textAlign: "center", minWidth: "6rem" }}
  >
    <Typography variant="h5" style={{ color }}>
      {value}
    </Typography>
    <Typography variant="caption">{label}</Typography>
  </Paper>
);

// Health summary for follow-up requests within a selectable time window. The
// request list is server-side paginated, so counts come from lightweight
// count-queries (totalMatches + startDate/status filters) rather than the page.
const FollowupHealth = () => {
  // captured at mount (recomputed on revisit) — keeps render pure
  const [now] = useState(() => Date.now());
  const [windowKey, setWindowKey] = useState("24h");
  const win =
    WINDOWS.find((w) => w.key === windowKey) ?? WINDOWS[WINDOWS.length - 1]!;
  const startDate =
    win.ms === Infinity ? undefined : new Date(now - win.ms).toISOString();

  const base: Record<string, any> = { numPerPage: 1, pageNumber: 1 };
  if (startDate) base["startDate"] = startDate;

  // Explicit (not mapped) so the hook count/order is stable per the rules of hooks.
  const total = useGetFollowupRequestsQuery(base).data?.totalMatches ?? 0;
  const completed =
    useGetFollowupRequestsQuery({ ...base, status: "completed" }).data
      ?.totalMatches ?? 0;
  const submitted =
    useGetFollowupRequestsQuery({ ...base, status: "submitted" }).data
      ?.totalMatches ?? 0;
  const pending =
    useGetFollowupRequestsQuery({ ...base, status: "pending" }).data
      ?.totalMatches ?? 0;
  const failed =
    useGetFollowupRequestsQuery({ ...base, status: "failed" }).data
      ?.totalMatches ?? 0;
  const deleted =
    useGetFollowupRequestsQuery({ ...base, status: "deleted" }).data
      ?.totalMatches ?? 0;
  const other = Math.max(
    0,
    total - completed - submitted - pending - failed - deleted,
  );

  const slices = [
    { label: "Completed", value: completed },
    { label: "Submitted", value: submitted },
    { label: "Pending", value: pending },
    { label: "Failed", value: failed },
    { label: "Deleted", value: deleted },
    { label: "Other", value: other },
  ];
  const nonZero = slices.filter((s) => s.value > 0);

  return (
    <Paper style={{ padding: "1rem", marginBottom: "1rem" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "0.5rem",
        }}
      >
        <Typography variant="h6">Follow-up request health</Typography>
        <ToggleButtonGroup
          size="small"
          exclusive
          value={windowKey}
          onChange={(_e, v) => v && setWindowKey(v)}
        >
          {WINDOWS.map((w) => (
            <ToggleButton key={w.key} value={w.key}>
              {w.label}
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
      </div>
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "1rem",
          alignItems: "center",
          marginTop: "0.5rem",
        }}
      >
        <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
          <Tile label="Total" value={total} />
          {nonZero.map((s) => (
            <Tile
              key={s.label}
              label={s.label}
              value={s.value}
              color={(COLORS as any)[s.label]}
            />
          ))}
        </div>
        <div style={{ flex: "1 1 260px", minWidth: 240 }}>
          {total === 0 ? (
            <Typography variant="body2" style={{ fontStyle: "italic" }}>
              No requests in this window.
            </Typography>
          ) : (
            <Plot
              data={[
                {
                  type: "pie",
                  hole: 0.4,
                  labels: nonZero.map((s) => s.label),
                  values: nonZero.map((s) => s.value),
                  marker: {
                    colors: nonZero.map((s) => (COLORS as any)[s.label]),
                  },
                  textinfo: "label+value",
                  sort: false,
                },
              ]}
              layout={{
                height: 230,
                margin: { t: 10, b: 10, l: 10, r: 10 },
                showlegend: false,
              }}
              config={{ displayModeBar: false }}
              style={{ width: "100%" }}
            />
          )}
        </div>
      </div>
    </Paper>
  );
};

export default FollowupHealth;
