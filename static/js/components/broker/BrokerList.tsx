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
import IconButton from "@mui/material/IconButton";
import MenuItem from "@mui/material/MenuItem";
import Radio from "@mui/material/Radio";
import Switch from "@mui/material/Switch";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";

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
import NewBrokerFilterDialog from "./NewBrokerFilterDialog";

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
  if (!isSystemAdmin) return "Only system admins can change the defaults.";
  if (b[toggle.field]) return "";
  if (!b.capabilities?.[toggle.capability]) return toggle.unsupported;
  if (!b.active) return "Activate this broker to make it the default.";
  return "";
};

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
  const [newFilterOpen, setNewFilterOpen] = useState(false);
  const [editing, setEditing] = useState<Broker | null>(null);
  const schema = newClass ? apis?.[newClass]?.formSchemaConfig : null;

  const openDialog = (broker: Broker | null) => {
    setEditing(broker);
    setNewName(broker?.name ?? "");
    setNewClass(broker?.broker_classname ?? "");
    setFormData(broker?.altdata ?? {});
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
    if ("data" in res) setAddOpen(false);
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
              onClick={() => openDialog(row)}
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
    <Box
      sx={{
        height: "calc(100vh - 5.25rem)",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          borderBottom: 1,
          borderColor: "divider",
          mb: 2,
        }}
      >
        <Tabs value={tab} onChange={(_event, value) => setTab(value)}>
          <Tab label="Brokers" />
          <Tab label="Filters" />
        </Tabs>
        {(tab === 1 || isSystemAdmin) && (
          <Button
            variant="contained"
            size="small"
            startIcon={<AddIcon />}
            onClick={() =>
              tab === 0 ? openDialog(null) : setNewFilterOpen(true)
            }
          >
            {tab === 0 ? "Broker" : "Filter"}
          </Button>
        )}
      </Box>

      {tab === 0 && (
        <StyledDataGrid
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
              navigate(`/brokers/${row.id}`);
          }}
          sx={{
            flex: 1,
            minHeight: 0,
            "& .MuiDataGrid-row": { cursor: "pointer" },
          }}
          data-testid="tour-brokers-list"
        />
      )}

      {tab === 1 && <FilterCatalog />}

      <NewBrokerFilterDialog
        open={newFilterOpen}
        onClose={() => setNewFilterOpen(false)}
      />

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
            <TextField
              select
              size="small"
              label="Provider"
              value={newClass}
              disabled={Boolean(editing)}
              onChange={(e) => {
                setNewClass(e.target.value);
                setFormData({});
              }}
              sx={{ minWidth: 220 }}
            >
              {Object.keys(apis || {}).map((c) => (
                <MenuItem key={c} value={c}>
                  {c}
                </MenuItem>
              ))}
            </TextField>
          </Box>
          {schema && (
            <Form
              id={NEW_BROKER_FORM_ID}
              schema={editing ? optionalSchema(schema) : schema}
              uiSchema={apis?.[newClass]?.uiSchema || {}}
              formData={formData}
              validator={validator}
              onChange={(e) => setFormData(e.formData)}
              onSubmit={onSubmit}
            >
              <></>
            </Form>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAddOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            disabled={!newName || !newClass}
            {...(schema
              ? ({ type: "submit", form: NEW_BROKER_FORM_ID } as const)
              : { onClick: onSubmit })}
          >
            {editing ? "Save changes" : "Create broker"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default BrokerList;
