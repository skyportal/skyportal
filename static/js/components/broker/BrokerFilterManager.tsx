import { useState } from "react";
import { Link } from "react-router-dom";

import Box from "@mui/material/Box";
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
import { useGetGroupsQuery } from "../../ducks/groups";
import { useGetStreamsQuery } from "../../ducks/streams";

const BrokerFilterManager = ({ brokerId }: { brokerId: number }) => {
  setBrokerFilterTarget(brokerId);

  const { data: filters } = useGetBrokerFiltersQuery(brokerId);
  const { data: groups } = useGetGroupsQuery();
  const { data: streams } = useGetStreamsQuery();

  const [search, setSearch] = useState("");
  const [groupId, setGroupId] = useState<number | "">("");

  // Show every filter the user can access (the API already scopes to those),
  // so any of them can be opened in the builder; badge the ones that already
  // carry a broker pipeline.
  const streamList = (streams as { id: number; name: string }[]) || [];
  const groupList = groups?.userAccessible || [];
  const groupName = (id: number) =>
    groupList.find((g) => g.id === id)?.name ?? `group ${id}`;
  const streamName = (id: number) =>
    streamList.find((s) => s.id === id)?.name ?? `stream ${id}`;
  const hasPipeline = (f: { altdata?: Record<string, unknown> }) =>
    Boolean((f.altdata as { boom?: unknown } | undefined)?.boom);

  const q = search.trim().toLowerCase();
  const accessibleFilters = (filters || []).filter(
    (f) =>
      (!q || f.name.toLowerCase().includes(q)) &&
      (groupId === "" || f.group_id === groupId),
  );

  return (
    <Box>
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 2,
          mb: 2,
        }}
      >
        <TextField
          size="small"
          label="Search"
          placeholder="Filter name"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <FormControl size="small" sx={{ minWidth: 180 }}>
          <InputLabel id="bf-group-filter">Group</InputLabel>
          <Select
            labelId="bf-group-filter"
            label="Group"
            value={groupId}
            onChange={(e) => setGroupId(e.target.value as number)}
          >
            <MenuItem value="">All groups</MenuItem>
            {groupList.map((g) => (
              <MenuItem key={g.id} value={g.id}>
                {g.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      {accessibleFilters.length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          {filters?.length
            ? "No filter matches this search."
            : "No accessible filters. Create one from the New filter tab."}
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
    </Box>
  );
};

export default BrokerFilterManager;
