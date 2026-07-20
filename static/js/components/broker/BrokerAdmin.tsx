import { useState } from "react";
import { Link } from "react-router-dom";

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
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Select from "@mui/material/Select";
import Switch from "@mui/material/Switch";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
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

// Admin/config view for every broker (searchable AND ingestion-only), where any
// provider can be configured, activated, and removed — distinct from the alert
// search page.
const BrokerAdmin = () => {
  const { data: brokers, isLoading } = useGetBrokersQuery();
  const { data: apis } = useGetBrokerAPIsQuery();
  const [createBroker] = useCreateBrokerMutation();
  const [updateBroker] = useUpdateBrokerMutation();
  const [deleteBroker] = useDeleteBrokerMutation();

  const [newClass, setNewClass] = useState("");
  const [newName, setNewName] = useState("");
  const [formData, setFormData] = useState<Record<string, unknown>>({});

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
        <Paper variant="outlined" sx={{ mb: 3, overflowX: "auto" }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Provider</TableCell>
                <TableCell>Surveys</TableCell>
                <TableCell>Capabilities</TableCell>
                <TableCell>Active</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {(brokers || []).map((b) => (
                <TableRow key={b.id}>
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
                  <TableCell>
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
                  <TableCell align="right">
                    {b.capabilities?.["query_alerts"] && (
                      <Button size="small" component={Link} to="/brokers">
                        Alerts
                      </Button>
                    )}
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

export default BrokerAdmin;
