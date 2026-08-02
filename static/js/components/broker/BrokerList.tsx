import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { withTheme } from "@rjsf/core";
import { Theme as MuiTheme } from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import DeleteIcon from "@mui/icons-material/Delete";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import FormControl from "@mui/material/FormControl";
import IconButton from "@mui/material/IconButton";
import InputLabel from "@mui/material/InputLabel";
import MuiLink from "@mui/material/Link";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Select from "@mui/material/Select";
import Switch from "@mui/material/Switch";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TableSortLabel from "@mui/material/TableSortLabel";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import {
  useCreateBrokerMutation,
  useDeleteBrokerMutation,
  useGetBrokerAPIsQuery,
  useGetBrokersQuery,
  useUpdateBrokerMutation,
} from "../../ducks/brokers";

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
];

// Admin/config view for every broker (searchable AND ingestion-only), where any
// provider can be configured, activated, and removed — distinct from the alert
// search page.
const BrokerList = () => {
  const navigate = useNavigate();
  const { data: brokers, isLoading } = useGetBrokersQuery();
  const { data: apis } = useGetBrokerAPIsQuery();
  const [createBroker] = useCreateBrokerMutation();
  const [updateBroker] = useUpdateBrokerMutation();
  const [deleteBroker] = useDeleteBrokerMutation();

  const [newClass, setNewClass] = useState("");
  const [newName, setNewName] = useState("");
  const [formData, setFormData] = useState<Record<string, unknown>>({});

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

  const onCreate = async () => {
    if (!newName || !newClass) return;
    const res = await createBroker({
      name: newName,
      broker_classname: newClass,
      altdata: formData,
    });
    if ("data" in res) {
      setNewName("");
      setNewClass("");
      setFormData({});
    }
  };

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h5" gutterBottom>
        Brokers
      </Typography>

      {isLoading ? (
        <CircularProgress />
      ) : (
        <>
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
                    <TableCell>
                      <MuiLink
                        component={Link}
                        to={brokerLink(b.id)}
                        onClick={(e) => e.stopPropagation()}
                      >
                        {b.name}
                      </MuiLink>
                    </TableCell>
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
                        onChange={(e) =>
                          updateBroker({
                            id: b.id,
                            patch: { active: e.target.checked },
                          })
                        }
                      />
                    </TableCell>
                    <TableCell
                      align="right"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <IconButton
                        size="small"
                        aria-label="delete broker"
                        onClick={() => deleteBroker(b.id)}
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Paper>
        </>
      )}

      <Typography variant="h6" gutterBottom>
        Add a broker
      </Typography>
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
        <Paper variant="outlined" sx={{ p: 2, maxWidth: 560 }}>
          <Form
            schema={schema as Record<string, unknown>}
            uiSchema={(uiSchema || {}) as Record<string, unknown>}
            formData={formData}
            validator={validator}
            onChange={(e) => setFormData(e.formData)}
            onSubmit={() => onCreate()}
          >
            <Button type="submit" variant="contained" disabled={!newName}>
              Create broker
            </Button>
          </Form>
        </Paper>
      ) : null}
    </Box>
  );
};

export default BrokerList;
