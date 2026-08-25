import { useState } from "react";
import { useNavigate } from "react-router-dom";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import TextField from "@mui/material/TextField";

import { useAttachFilterToBrokerMutation } from "../../ducks/brokers";
import { useAddGroupFilterMutation } from "../../ducks/filter";
import { useGetGroupsQuery } from "../../ducks/groups";
import { useGetStreamsQuery } from "../../ducks/streams";

const NewBrokerFilterForm = ({ brokerId }: { brokerId: number }) => {
  const navigate = useNavigate();
  const [addGroupFilter] = useAddGroupFilterMutation();
  const [attachFilter] = useAttachFilterToBrokerMutation();

  const { data: groups } = useGetGroupsQuery();
  const { data: streams } = useGetStreamsQuery();

  const [name, setName] = useState("");
  const [groupId, setGroupId] = useState<number | "">("");
  const [streamId, setStreamId] = useState<number | "">("");

  const onCreate = async () => {
    if (!name || groupId === "" || streamId === "") return;
    try {
      const created = (await addGroupFilter({
        name,
        group_id: groupId,
        stream_id: streamId,
      }).unwrap()) as { id?: number };
      if (created?.id) {
        await attachFilter({ filterId: created.id, brokerId }).unwrap();
        navigate(`/brokers/${brokerId}/filter/${created.id}`);
      }
    } catch {
      // error notification is surfaced by the base query
    }
  };

  return (
    <Box
      sx={{ display: "flex", gap: 2, alignItems: "center", flexWrap: "wrap" }}
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
  );
};

export default NewBrokerFilterForm;
