import { ReactNode, useState } from "react";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import RefreshIcon from "@mui/icons-material/Refresh";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { skipToken } from "@reduxjs/toolkit/query";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import JsonDashboard from "react-json-dashboard";
import { Link, useNavigate } from "react-router-dom";

import { showNotification } from "baselayer/components/Notifications";
import withRouter from "../withRouter";
import useTabParam from "../../hooks/useTabParam";
import { useAppDispatch } from "../../types/hooks";
import {
  useDeleteInstrumentMutation,
  useGetInstrumentQuery,
  useUpdateInstrumentStatusMutation,
} from "../../ducks/instrument";
import { useGetProfileQuery } from "../../ducks/profile";
import { useGetTelescopeQuery } from "../../ducks/telescopes";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import InstrumentForm from "./InstrumentForm";
import InstrumentLogs from "./InstrumentLogs";
import { QuadrantGrid } from "./ZtfQuadrantsField";
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
  const [deleteInstrument] = useDeleteInstrumentMutation();
  const navigate = useNavigate();
  const profile = useGetProfileQuery().data;
  const permissions = profile?.permissions ?? [];
  const canManage =
    permissions.includes("Manage instruments") ||
    permissions.includes("System admin");
  const canEdit =
    canManage ||
    (profile?.id != null && instrument?.created_by_id === profile.id);
  const [tab, setTab] = useTabParam(["overview", "logs", "status"]);
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  if (instrument?.id !== Number(route.id)) return <Spinner />;

  const {
    specific_configuration: specificConfiguration,
    missing_quadrants: missingQuadrants,
    ...generalConfiguration
  } = (instrument.configuration_data ?? {}) as Record<string, any>;
  const configuration = Object.entries({
    ...generalConfiguration,
    ...specificConfiguration,
  });
  const sensitivity = instrument.sensitivity_data ?? {};

  const handleDelete = async () => {
    const { error } = await deleteInstrument(route.id);
    if (error) return;
    dispatch(showNotification("Instrument deleted"));
    navigate("/instruments");
  };

  const refreshStatus = async () => {
    const { error } = await updateInstrumentStatus(route.id);
    if (!error) dispatch(showNotification("Instrument status updated"));
  };

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <Box
        sx={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
        }}
      >
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
        <Box sx={{ display: "flex", gap: 0.5 }}>
          {canEdit && (
            <Tooltip title="Edit instrument">
              <IconButton onClick={() => setEditOpen(true)}>
                <EditIcon />
              </IconButton>
            </Tooltip>
          )}
          {canManage && (
            <Tooltip title="Delete instrument">
              <IconButton color="error" onClick={() => setDeleteOpen(true)}>
                <DeleteIcon />
              </IconButton>
            </Tooltip>
          )}
        </Box>
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
            columnCount: { xs: 1, lg: 2 },
            columnGap: 2,
            "& > *": { breakInside: "avoid", mb: 2 },
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
                ["Default observer", instrument.default_observer],
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
          {instrument.name === "ZTF" && (
            <Section title="Active quadrants">
              <Typography variant="body2" color="text.secondary">
                {64 - (missingQuadrants?.length ?? 0)} / 64
              </Typography>
              <QuadrantGrid missing={missingQuadrants ?? []} />
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
      <Dialog open={editOpen} onClose={() => setEditOpen(false)} maxWidth="md">
        <DialogTitle>Edit {instrument.name} instrument</DialogTitle>
        <DialogContent dividers>
          <InstrumentForm
            onClose={() => setEditOpen(false)}
            instrumentId={instrument.id}
          />
        </DialogContent>
      </Dialog>
      <ConfirmDeletionDialog
        deleteFunction={handleDelete}
        dialogOpen={deleteOpen}
        closeDialog={() => setDeleteOpen(false)}
        resourceName="instrument"
      />
    </Box>
  );
};

export default withRouter(Instrument);
