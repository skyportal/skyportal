import { useMemo, useState } from "react";
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
import Paper from "@mui/material/Paper";
import Radio from "@mui/material/Radio";
import Select from "@mui/material/Select";
import Switch from "@mui/material/Switch";
import Tab from "@mui/material/Tab";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TableSortLabel from "@mui/material/TableSortLabel";
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
import FilterCatalog from "./FilterCatalog";

const Form = withTheme(MuiTheme);

// Which of the unified capabilities a broker actually exposes.
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

const COLUMNS = [
  { id: "name", label: "Name", value: (b: any) => b.name || "" },
  {
    id: "provider",
    label: "Provider",
    value: (b: any) => b.broker_classname || "",
  },
  {
    id: "surveys",
    label: "Surveys",
    value: (b: any) => (b.surveys || []).join(", "),
  },
  {
    id: "capabilities",
    label: "Capabilities",
    value: (b: any) =>
      capabilityChips(b.capabilities)
        .map((c) => c.label)
        .join(", "),
  },
  {
    id: "active",
    label: "Active",
    value: (b: any) => Number(Boolean(b.active)),
  },
  {
    id: "default_alert_search",
    label: "Default search",
    value: (b: any) => Number(Boolean(b.default_alert_search)),
  },
  {
    id: "default_crossmatch",
    label: "Default cross-match",
    value: (b: any) => Number(Boolean(b.default_crossmatch)),
  },
];

const DEFAULT_TOGGLES = [
  {
    field: "default_alert_search",
    capability: "query_alerts",
    unsupported: "This broker does not support alert search.",
  },
  {
    field: "default_crossmatch",
    capability: "cross_match_catalogs",
    unsupported: "This broker does not support catalog cross-match.",
  },
] as const;

// Admin/config view for every broker (searchable AND ingestion-only), where any
// provider can be configured, activated, and removed — distinct from the alert
// search page.
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

  const [tab, setTab] = useState(0);
  const [addOpen, setAddOpen] = useState(false);
  const [editing, setEditing] = useState<Broker | null>(null);
  const [orderBy, setOrderBy] = useState("name");
  const [order, setOrder] = useState<"asc" | "desc">("asc");

  const sortedBrokers = useMemo(() => {
    const col = COLUMNS.find((c) => c.id === orderBy);
    if (!col) return brokers || [];
    const dir = order === "asc" ? 1 : -1;
    return [...(brokers || [])].sort((a, b) => {
      const va = col.value(a);
      const vb = col.value(b);
      if (typeof va === "number" && typeof vb === "number")
        return (va - vb) * dir;
      return String(va).localeCompare(String(vb)) * dir;
    });
  }, [brokers, orderBy, order]);

  const onSort = (id: string) => {
    setOrder(orderBy === id && order === "asc" ? "desc" : "asc");
    setOrderBy(id);
  };

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

      {tab === 0 &&
        (isLoading ? (
          <CircularProgress />
        ) : (
          <Paper variant="outlined" sx={{ mb: 3, overflowX: "auto" }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  {COLUMNS.map((c) => (
                    <TableCell
                      key={c.id}
                      sortDirection={orderBy === c.id ? order : false}
                    >
                      <TableSortLabel
                        active={orderBy === c.id}
                        direction={orderBy === c.id ? order : "asc"}
                        onClick={() => onSort(c.id)}
                      >
                        {c.label}
                      </TableSortLabel>
                    </TableCell>
                  ))}
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {sortedBrokers.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={COLUMNS.length + 1}>
                      <Typography variant="body2" color="text.secondary">
                        No broker configured yet.
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
                {sortedBrokers.map((b) => (
                  <TableRow
                    key={b.id}
                    hover
                    onClick={() => navigate(brokerLink(b.id))}
                    sx={{ cursor: "pointer" }}
                  >
                    <TableCell>{b.name}</TableCell>
                    <TableCell>{b.broker_classname}</TableCell>
                    <TableCell>{(b.surveys || []).join(", ")}</TableCell>
                    <TableCell>
                      {capabilityChips(b.capabilities).map((c) => (
                        <Chip
                          key={c.label}
                          size="small"
                          label={c.label}
                          sx={{ mr: 0.5 }}
                        />
                      ))}
                    </TableCell>
                    <TableCell onClick={(e) => e.stopPropagation()}>
                      <Switch
                        checked={b.active}
                        disabled={!isSystemAdmin}
                        onChange={(e) =>
                          updateBroker({
                            id: b.id,
                            patch: { active: e.target.checked },
                          })
                        }
                      />
                    </TableCell>
                    {DEFAULT_TOGGLES.map(
                      ({ field, capability, unsupported }) => {
                        const reason = !b.capabilities?.[capability]
                          ? unsupported
                          : !b.active
                            ? "Activate this broker to make it the default."
                            : !isSystemAdmin
                              ? "Only system admins can change the defaults."
                              : "";
                        return (
                          <TableCell
                            key={field}
                            onClick={(e) => e.stopPropagation()}
                          >
                            <Tooltip title={reason}>
                              <span>
                                <Radio
                                  size="small"
                                  checked={Boolean(b[field])}
                                  disabled={Boolean(reason)}
                                  onChange={() =>
                                    updateBroker({
                                      id: b.id,
                                      patch: { [field]: true },
                                    })
                                  }
                                />
                              </span>
                            </Tooltip>
                          </TableCell>
                        );
                      },
                    )}
                    <TableCell
                      align="right"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {isSystemAdmin && (
                        <>
                          <IconButton
                            size="small"
                            aria-label="edit broker"
                            onClick={() => openEdit(b)}
                          >
                            <EditIcon fontSize="small" />
                          </IconButton>
                          <IconButton
                            size="small"
                            aria-label="delete broker"
                            onClick={() => deleteBroker(b.id)}
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Paper>
        ))}

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
