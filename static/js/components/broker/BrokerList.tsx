import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { withTheme } from "@rjsf/core";
import { Theme as MuiTheme } from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import FormControl from "@mui/material/FormControl";
import IconButton from "@mui/material/IconButton";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Radio from "@mui/material/Radio";
import Select from "@mui/material/Select";
import Switch from "@mui/material/Switch";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";

import {
  Broker,
  useCreateBrokerMutation,
  useDeleteBrokerMutation,
  useGetBrokerAPIsQuery,
  useGetBrokersQuery,
  useUpdateBrokerMutation,
} from "../../ducks/brokers";
import { useGetProfileQuery } from "../../ducks/profile";
import StyledDataGrid from "../StyledDataGrid";
import FilterCatalog from "./FilterCatalog";

const Form = withTheme(MuiTheme);

const capabilityChips = (caps: Record<string, boolean>) =>
  [
    { label: "search", on: Boolean(caps?.["query_alerts"]) },
    { label: "ingest", on: Boolean(caps?.["run_ingestion"]) },
    {
      label: "filter",
      on: Boolean(caps?.["filter_modules"] || caps?.["test_filter"]),
    },
  ].filter((c) => c.on);

const brokerLink = (id: number) => `/brokers/${id}`;

const TABS = ["Brokers", "Filters"];

const NEW_BROKER_FORM_ID = "new-broker-form";

const optionalSchema = (node: any): any => {
  if (!node || typeof node !== "object") return node;
  const { required, properties, ...rest } = node;
  return {
    ...rest,
    ...(properties
      ? {
          properties: Object.fromEntries(
            Object.entries(properties).map(([k, v]) => [k, optionalSchema(v)]),
          ),
        }
      : {}),
  };
};

const DEFAULT_TOGGLES = [
  {
    field: "default_alert_search",
    label: "Default search",
    description:
      "Broker the source page's \"Search alerts\" button and the sidebar's " +
      "alert search open. Unset: no alert search is offered.",
    capability: "query_alerts",
    unsupported: "This broker does not support alert search.",
  },
  {
    field: "default_crossmatch",
    label: "Default cross-match",
    description:
      "Broker the source page's centroid plot cross-matches against " +
      "(cone search on reference catalogs). Unset: the first broker that " +
      "returns catalogs is used.",
    capability: "cross_match_catalogs",
    unsupported: "This broker does not support catalog cross-match.",
  },
  {
    field: "default_photometry",
    label: "Default photometry",
    description:
      "Broker the source page's lightcurve pulls photometry from on the fly, " +
      "shown on top of the saved points and never written to the database. " +
      "Unset: only saved photometry is shown, and no broker is queried.",
    capability: "get_photometry",
    unsupported:
      "This broker cannot serve the source page's photometry: it has no " +
      "object fetch, or its fetch is too slow to sit in a page load.",
  },
] as const;

const defaultBlockedReason = (
  b: any,
  toggle: (typeof DEFAULT_TOGGLES)[number],
  isSystemAdmin: boolean,
) => {
  const clearing = Boolean(b[toggle.field]);
  if (!isSystemAdmin) return "Only system admins can change the defaults.";
  if (clearing) return "";
  if (!b.capabilities?.[toggle.capability]) return toggle.unsupported;
  if (!b.active) return "Activate this broker to make it the default.";
  return "";
};

// Admin view for every broker, distinct from the alert search page.
const BrokerList = () => {
  const navigate = useNavigate();
  const { data: brokers, isLoading } = useGetBrokersQuery();
  const { data: apis } = useGetBrokerAPIsQuery();
  const { data: profile } = useGetProfileQuery();
  const isSystemAdmin = Boolean(profile?.permissions?.includes("System admin"));
  const [createBroker] = useCreateBrokerMutation();
  const [updateBroker] = useUpdateBrokerMutation();
  const [deleteBroker] = useDeleteBrokerMutation();

  const [newClass, setNewClass] = useState("");
  const [newName, setNewName] = useState("");
  const [formData, setFormData] = useState<Record<string, unknown>>({});

  const [pendingDefaults, setPendingDefaults] = useState<string[]>([]);
  const [tab, setTab] = useState(0);
  const [addOpen, setAddOpen] = useState(false);
  const [editing, setEditing] = useState<Broker | null>(null);
  const classNames = Object.keys(apis || {});
  const schema = newClass ? apis?.[newClass]?.formSchemaConfig : null;
  const uiSchema = newClass ? apis?.[newClass]?.uiSchema : null;
  const dialogSchema = editing ? optionalSchema(schema) : schema;

  const openCreate = () => {
    setEditing(null);
    setNewName("");
    setNewClass("");
    setFormData({});
    setAddOpen(true);
  };

  const openEdit = (broker: Broker) => {
    setEditing(broker);
    setNewName(broker.name);
    setNewClass(broker.broker_classname);
    setFormData((broker.altdata as Record<string, unknown>) ?? {});
    setAddOpen(true);
  };

  const onSubmit = async () => {
    if (!newName || !newClass) return;
    const res = editing
      ? await updateBroker({
          id: editing.id,
          patch: { name: newName, altdata: formData },
        })
      : await createBroker({
          name: newName,
          broker_classname: newClass,
          altdata: formData,
        });
    if ("data" in res) {
      setNewName("");
      setNewClass("");
      setFormData({});
      setEditing(null);
      setAddOpen(false);
    }
  };

  const columns: any[] = [
    { field: "name", headerName: "Name", flex: 1, minWidth: 140 },
    {
      field: "broker_classname",
      headerName: "Provider",
      flex: 1,
      minWidth: 140,
    },
    {
      field: "surveys",
      headerName: "Surveys",
      minWidth: 120,
      valueGetter: (value: string[] | undefined) => (value || []).join(", "),
    },
    {
      field: "capabilities",
      headerName: "Capabilities",
      minWidth: 200,
      valueGetter: (value: Record<string, boolean>) =>
        capabilityChips(value)
          .map((c) => c.label)
          .join(", "),
      renderCell: ({ row }: { row: Broker }) =>
        capabilityChips(row.capabilities).map((c) => (
          <Chip key={c.label} size="small" label={c.label} sx={{ mr: 0.5 }} />
        )),
    },
    {
      field: "active",
      headerName: "Active",
      renderCell: ({ row }: { row: Broker }) => (
        <Switch
          checked={row.active}
          disabled={!isSystemAdmin}
          onChange={(e) =>
            updateBroker({ id: row.id, patch: { active: e.target.checked } })
          }
        />
      ),
    },
    {
      field: "ingest",
      headerName: "Ingest",
      description:
        "Consume this broker's stream continuously and save what it sends. " +
        "Only offered by brokers whose provider supports ingestion.",
      renderCell: ({ row }: { row: Broker }) => (
        <Switch
          checked={Boolean(row.ingest)}
          disabled={!isSystemAdmin || !row.capabilities?.["run_ingestion"]}
          onChange={(e) =>
            updateBroker({ id: row.id, patch: { ingest: e.target.checked } })
          }
        />
      ),
    },
    ...DEFAULT_TOGGLES.map((toggle) => ({
      field: toggle.field,
      headerName: toggle.label,
      description: toggle.description,
      minWidth: 150,
      renderCell: ({ row }: { row: Broker }) => {
        const isDefault = Boolean(row[toggle.field]);
        const blocked = defaultBlockedReason(row, toggle, isSystemAdmin);
        const pendingKey = `${row.id}:${toggle.field}`;
        return pendingDefaults.includes(pendingKey) ? (
          <CircularProgress size={20} sx={{ m: "5px" }} />
        ) : (
          <Tooltip
            title={blocked || (isDefault ? "Click to clear this default." : "")}
          >
            <span>
              <Radio
                size="small"
                checked={isDefault}
                disabled={Boolean(blocked)}
                onClick={async () => {
                  setPendingDefaults((p) => [...p, pendingKey]);
                  await updateBroker({
                    id: row.id,
                    patch: { [toggle.field]: !isDefault },
                  });
                  setPendingDefaults((p) => p.filter((k) => k !== pendingKey));
                }}
              />
            </span>
          </Tooltip>
        );
      },
    })),
    {
      field: "actions",
      headerName: "Actions",
      align: "right",
      headerAlign: "right",
      sortable: false,
      filterable: false,
      renderCell: ({ row }: { row: Broker }) =>
        isSystemAdmin && (
          <>
            <IconButton
              size="small"
              aria-label="edit broker"
              onClick={() => openEdit(row)}
            >
              <EditIcon fontSize="small" />
            </IconButton>
            <IconButton
              size="small"
              aria-label="delete broker"
              onClick={() => deleteBroker(row.id)}
            >
              <DeleteIcon fontSize="small" />
            </IconButton>
          </>
        ),
    },
  ];

  return (
    <Box sx={{ p: 2 }}>
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 1,
          mb: 1,
        }}
      >
        <Typography variant="h5">Brokers</Typography>
        {isSystemAdmin && (
          <Button
            variant="contained"
            size="small"
            startIcon={<AddIcon />}
            onClick={openCreate}
          >
            Add a broker
          </Button>
        )}
      </Box>

      <Tabs
        sx={{ borderBottom: 1, borderColor: "divider", mb: 2 }}
        value={tab}
        onChange={(_event, value) => setTab(value)}
      >
        {TABS.map((label) => (
          <Tab key={label} label={label} />
        ))}
      </Tabs>

      {tab === 0 && (
        <StyledDataGrid
          autoHeight
          rows={brokers || []}
          columns={columns}
          loading={isLoading}
          localeText={{ noRowsLabel: "No broker configured yet." }}
          initialState={{
            sorting: { sortModel: [{ field: "name", sort: "asc" }] },
          }}
          onCellClick={({ field, row }: { field: string; row: Broker }) => {
            if (
              ["name", "broker_classname", "surveys", "capabilities"].includes(
                field,
              )
            )
              navigate(brokerLink(row.id));
          }}
          sx={{ mb: 3, "& .MuiDataGrid-row": { cursor: "pointer" } }}
          data-testid="tour-brokers-list"
        />
      )}

      {tab === 1 && <FilterCatalog />}

      <Dialog
        open={addOpen}
        onClose={() => setAddOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          {editing ? `Edit ${editing.name}` : "Add a broker"}
        </DialogTitle>
        <DialogContent dividers>
          <Box sx={{ display: "flex", gap: 2, mb: 2, flexWrap: "wrap" }}>
            <TextField
              size="small"
              label="Name"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
            />
            <FormControl size="small" sx={{ minWidth: 220 }}>
              <InputLabel id="new-broker-class">Provider</InputLabel>
              <Select
                labelId="new-broker-class"
                label="Provider"
                value={newClass}
                disabled={Boolean(editing)}
                onChange={(e) => {
                  setNewClass(e.target.value);
                  setFormData({});
                }}
              >
                {classNames.map((c) => (
                  <MenuItem key={c} value={c}>
                    {c}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>
          {schema ? (
            <Form
              id={NEW_BROKER_FORM_ID}
              schema={dialogSchema as Record<string, unknown>}
              uiSchema={(uiSchema || {}) as Record<string, unknown>}
              formData={formData}
              validator={validator}
              onChange={(e) => setFormData(e.formData)}
              onSubmit={() => onSubmit()}
            >
              <></>
            </Form>
          ) : null}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAddOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            disabled={!newName || !newClass}
            {...(schema
              ? ({ type: "submit", form: NEW_BROKER_FORM_ID } as const)
              : { onClick: () => onSubmit() })}
          >
            {editing ? "Save changes" : "Create broker"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default BrokerList;
