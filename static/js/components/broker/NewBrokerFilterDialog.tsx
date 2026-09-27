import { useState } from "react";
import { useNavigate } from "react-router-dom";

import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";

import {
  useAttachFilterToBrokerMutation,
  useGetBrokersQuery,
} from "../../ducks/brokers";
import { useAddGroupFilterMutation } from "../../ducks/filter";
import { useGetGroupsQuery } from "../../ducks/groups";
import { useGetStreamsQuery } from "../../ducks/streams";

interface NewBrokerFilterDialogProps {
  open: boolean;
  onClose: () => void;
  brokerId?: number;
}

const NewBrokerFilterDialog = ({
  open,
  onClose,
  brokerId,
}: NewBrokerFilterDialogProps) => {
  const navigate = useNavigate();
  const [addGroupFilter] = useAddGroupFilterMutation();
  const [attachFilter] = useAttachFilterToBrokerMutation();

  const { data: groups } = useGetGroupsQuery();
  const { data: streams } = useGetStreamsQuery();
  const { data: brokers } = useGetBrokersQuery();

  const [name, setName] = useState("");
  const [groupId, setGroupId] = useState<number | "">("");
  const [streamId, setStreamId] = useState<number | "">("");
  const [selectedBroker, setSelectedBroker] = useState<number | "">("");
  const targetBroker = brokerId ?? selectedBroker;
  const incomplete =
    !name || groupId === "" || streamId === "" || targetBroker === "";

  const onCreate = async () => {
    if (incomplete) return;
    try {
      const created = (await addGroupFilter({
        name,
        group_id: groupId,
        stream_id: streamId,
      }).unwrap()) as { id?: number };
      if (created?.id) {
        await attachFilter({
          filterId: created.id,
          brokerId: targetBroker,
        }).unwrap();
        navigate(`/brokers/${targetBroker}/filter/${created.id}`);
      }
    } catch {
      // error notification is surfaced by the base query
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>New filter</DialogTitle>
      <DialogContent dividers>
        <Stack spacing={2}>
          <TextField
            size="small"
            label="Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <TextField
            select
            size="small"
            label="Group"
            value={groupId}
            onChange={(e) => setGroupId(Number(e.target.value))}
          >
            {(groups?.userAccessible || []).map((g) => (
              <MenuItem key={g.id} value={g.id}>
                {g.name}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            select
            size="small"
            label="Stream"
            value={streamId}
            onChange={(e) => setStreamId(Number(e.target.value))}
          >
            {((streams as { id: number; name: string }[]) || []).map((s) => (
              <MenuItem key={s.id} value={s.id}>
                {s.name}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            select
            size="small"
            label="Broker"
            value={targetBroker}
            disabled={brokerId !== undefined}
            onChange={(e) => setSelectedBroker(Number(e.target.value))}
          >
            {(brokers || [])
              .filter(
                (b) =>
                  b.id === brokerId || (b.active && b.filter_kind !== "none"),
              )
              .map((b) => (
                <MenuItem key={b.id} value={b.id}>
                  {b.name}
                </MenuItem>
              ))}
          </TextField>
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" disabled={incomplete} onClick={onCreate}>
          Create filter
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default NewBrokerFilterDialog;
