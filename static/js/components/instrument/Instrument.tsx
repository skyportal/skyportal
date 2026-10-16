import { ReactNode } from "react";
import RefreshIcon from "@mui/icons-material/Refresh";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import IconButton from "@mui/material/IconButton";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Typography from "@mui/material/Typography";
import { skipToken } from "@reduxjs/toolkit/query";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import JsonDashboard from "react-json-dashboard";
import { Link } from "react-router-dom";

import { showNotification } from "baselayer/components/Notifications";
import withRouter from "../withRouter";
import useTabParam from "../../hooks/useTabParam";
import { useAppDispatch } from "../../types/hooks";
import {
  useGetInstrumentQuery,
  useUpdateInstrumentStatusMutation,
} from "../../ducks/instrument";
import { useGetTelescopeQuery } from "../../ducks/telescopes";
import InstrumentLogs from "./InstrumentLogs";
import Paper from "../Paper";
import Spinner from "../Spinner";

dayjs.extend(utc);

const humanize = (key: string) =>
  key.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());

const formatValue = (value: unknown) =>
  typeof value === "number"
    ? String(Number(value.toFixed(4)))
    : typeof value === "object"
      ? JSON.stringify(value)
      : String(value);

const Section = ({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) => (
  <Paper sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
    <Typography variant="h6">{title}</Typography>
    {children}
  </Paper>
);

const Fields = ({ fields }: { fields: [string, unknown][] }) => (
  <Box
    sx={{
      display: "grid",
      gridTemplateColumns: "repeat(auto-fill, minmax(11rem, 1fr))",
      gap: 2,
    }}
  >
    {fields
      .filter(([, value]) => value != null && value !== "")
      .map(([label, value]) => (
        <Box key={label} sx={{ minWidth: 0 }}>
          <Typography variant="caption" color="text.secondary">
            {label}
          </Typography>
          <Typography variant="body2" sx={{ overflowWrap: "anywhere" }}>
            {formatValue(value)}
          </Typography>
        </Box>
      ))}
  </Box>
);

const SensitivityTable = ({
  sensitivity,
}: {
  sensitivity: Record<string, any>;
}) => {
  const rows: [string, Record<string, unknown>][] = Object.entries(sensitivity);
  const keys = [...new Set(rows.flatMap(([, values]) => Object.keys(values)))];
  return (
    <Box
      component="table"
      sx={{
        borderCollapse: "collapse",
        fontSize: "0.875rem",
        "& th, & td": {
          textAlign: "left",
          py: 0.75,
          pr: 2,
          borderBottom: 1,
          borderColor: "divider",
        },
        "& th": { color: "text.secondary", fontWeight: 500 },
      }}
    >
      <thead>
        <tr>
          <th>Filter</th>
          {keys.map((key) => (
            <th key={key}>{humanize(key)}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map(([filter, values]) => (
          <tr key={filter}>
            <td>{filter}</td>
            {keys.map((key) => (
              <td key={key}>
                {values[key] != null ? formatValue(values[key]) : ""}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </Box>
  );
};

interface InstrumentProps {
  route: {
    id: number;
  };
}

const Instrument = ({ route }: InstrumentProps) => {
  const dispatch = useAppDispatch();
  const { data: instrument } = useGetInstrumentQuery(route.id);
  const { data: telescope } = useGetTelescopeQuery(
    instrument?.telescope_id ?? skipToken,
  );
  const [updateInstrumentStatus] = useUpdateInstrumentStatusMutation();
  const [tab, setTab] = useTabParam(["overview", "logs", "status"]);

  if (instrument?.id !== Number(route.id)) return <Spinner />;

  const configuration = Object.entries(instrument.configuration_data ?? {});
  const sensitivity = instrument.sensitivity_data ?? {};

  const refreshStatus = async () => {
    const { error } = await updateInstrumentStatus(route.id);
    if (!error) dispatch(showNotification("Instrument status updated"));
  };

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <Box>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <Typography variant="h5">{instrument.name}</Typography>
          <Chip label={instrument.type} size="small" variant="outlined" />
        </Box>
        {telescope ? (
          <Link to={`/telescope/${instrument.telescope_id}`}>
            {telescope["name"]} ({telescope["nickname"]})
          </Link>
        ) : (
          <CircularProgress size={20} />
        )}
      </Box>
      <Tabs
        value={tab}
        onChange={(_e, value) => setTab(value)}
        sx={{ borderBottom: 1, borderColor: "divider" }}
      >
        <Tab label="Overview" />
        <Tab label="Logs" />
        <Tab label="Status" />
      </Tabs>
      {tab === 0 && (
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", lg: "1fr 1fr" },
            gap: 2,
            alignItems: "start",
          }}
        >
          <Section title="Details">
            <Fields
              fields={[
                ["Band", instrument.band],
                ["Follow-up API", instrument.api_classname],
                ["Observation plan API", instrument.api_classname_obsplan],
                ["Listener", instrument.listener_classname],
                ["TNS ID", instrument.tns_id],
                ["Treasure Map ID", instrument.treasuremap_id],
                ["ACROSS ID", instrument.across_id],
                ["Fields", instrument.has_fields ? "Yes" : "No"],
                ["Footprint", instrument.has_region ? "Yes" : "No"],
                [
                  "Created",
                  dayjs.utc(instrument.created_at).format("YYYY-MM-DD"),
                ],
              ]}
            />
          </Section>
          <Section title="Filters">
            {instrument.filters?.length ? (
              <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
                {instrument.filters.map((filter) => (
                  <Chip key={filter} label={filter} size="small" />
                ))}
              </Box>
            ) : (
              <Typography variant="body2" color="text.secondary">
                No filters
              </Typography>
            )}
          </Section>
          {configuration.length > 0 && (
            <Section title="Configuration">
              <Fields
                fields={configuration.map(([key, value]) => [
                  humanize(key),
                  value,
                ])}
              />
            </Section>
          )}
          {Object.keys(sensitivity).length > 0 && (
            <Section title="Sensitivity">
              <SensitivityTable sensitivity={sensitivity} />
            </Section>
          )}
          {instrument.acknowledgment && (
            <Section title="Acknowledgment">
              <Typography variant="body2">
                {instrument.acknowledgment}
              </Typography>
            </Section>
          )}
        </Box>
      )}
      {tab === 1 && (
        <InstrumentLogs
          instrumentId={Number(route.id)}
          logExists={Boolean(instrument.log_exists)}
        />
      )}
      {tab === 2 && (
        <Paper>
          <JsonDashboard
            title={`${instrument.name} Status`}
            data={instrument.status || {}}
            lastUpdated={instrument.last_status_update}
            refreshButton={
              <IconButton
                color="primary"
                aria-label="refresh"
                sx={{ m: 0, p: 0 }}
                onClick={refreshStatus}
              >
                <RefreshIcon />
              </IconButton>
            }
          />
        </Paper>
      )}
    </Box>
  );
};

export default withRouter(Instrument);
