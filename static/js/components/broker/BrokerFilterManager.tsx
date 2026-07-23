import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import { setBrokerFilterTarget } from "../../ducks/brokerFilterTarget";
import { useGetBrokerFiltersQuery } from "../../ducks/brokers";
import { useAddGroupFilterMutation } from "../../ducks/filter";
import { useGetGroupsQuery } from "../../ducks/groups";
import { useGetStreamsQuery } from "../../ducks/streams";

// Lists a pipeline-broker's filters and lets the user create a new one, linking
// each to the full builder page (BoomFilterPlugins) at /brokers/{id}/filter/{fid}.
const BrokerFilterManager = ({ brokerId }: { brokerId: number }) => {
  const navigate = useNavigate();
  const [addGroupFilter] = useAddGroupFilterMutation();
  setBrokerFilterTarget(brokerId);

  const { data: filters } = useGetBrokerFiltersQuery(brokerId);
  const { data: groups } = useGetGroupsQuery();
  const { data: streams } = useGetStreamsQuery();

  const [name, setName] = useState("");
  const [groupId, setGroupId] = useState<number | "">("");
  const [streamId, setStreamId] = useState<number | "">("");

  // Show every filter the user can access (the API already scopes to those),
  // so any of them can be opened in the builder; badge the ones that already
  // carry a broker pipeline.
  const streamList = (streams as { id: number; name: string }[]) || [];
  const groupName = (id: number) =>
    (groups?.userAccessible || []).find((g) => g.id === id)?.name ??
    `group ${id}`;
  const streamName = (id: number) =>
    streamList.find((s) => s.id === id)?.name ?? `stream ${id}`;
  const hasPipeline = (f: { altdata?: Record<string, unknown> }) =>
    Boolean((f.altdata as { boom?: unknown } | undefined)?.boom);
  const accessibleFilters = filters || [];

  const onCreate = async () => {
    if (!name || groupId === "" || streamId === "") return;
    try {
      const created = (await addGroupFilter({
        name,
        group_id: groupId,
        stream_id: streamId,
      }).unwrap()) as { id?: number };
      if (created?.id) {
        navigate(`/brokers/${brokerId}/filter/${created.id}`);
      }
    } catch {
      // error notification is surfaced by the base query
    }
  };

  return (
    <Box sx={{ mt: 2 }}>
      <Typography variant="subtitle1" gutterBottom>
        Filters
      </Typography>
      {accessibleFilters.length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          No accessible filters. Create one below.
        </Typography>
      ) : (
        <List dense>
          {accessibleFilters.map((f) => (
            <ListItem
              key={f.id}
              disablePadding
              secondaryAction={
                hasPipeline(f) ? (
                  <Chip size="small" label="pipeline" color="primary" />
                ) : null
              }
            >
              <ListItemButton
                component={Link}
                to={`/brokers/${brokerId}/filter/${f.id}`}
              >
                <ListItemText
                  primary={f.name}
                  secondary={`${groupName(f.group_id)} · ${streamName(f.stream_id)}`}
                />
              </ListItemButton>
            </ListItem>
          ))}
        </List>
      )}
      <Box
        sx={{
          display: "flex",
          gap: 2,
          alignItems: "center",
          mt: 2,
          flexWrap: "wrap",
        }}
      >
        <TextField
          size="small"
          label="New filter name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <FormControl size="small" sx={{ minWidth: 160 }}>
          <InputLabel id="bf-group">Group</InputLabel>
          <Select
            labelId="bf-group"
            label="Group"
            value={groupId}
            onChange={(e) => setGroupId(e.target.value as number)}
          >
            {(groups?.userAccessible || []).map((g) => (
              <MenuItem key={g.id} value={g.id}>
                {g.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 160 }}>
          <InputLabel id="bf-stream">Stream</InputLabel>
          <Select
            labelId="bf-stream"
            label="Stream"
            value={streamId}
            onChange={(e) => setStreamId(e.target.value as number)}
          >
            {((streams as { id: number; name: string }[]) || []).map((s) => (
              <MenuItem key={s.id} value={s.id}>
                {s.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <Button
          variant="contained"
          onClick={onCreate}
          disabled={!name || groupId === "" || streamId === ""}
        >
          Create filter
        </Button>
      </Box>
    </Box>
  );
};

export default BrokerFilterManager;
