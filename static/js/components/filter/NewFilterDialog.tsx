import { type FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";

import { useGetBrokersQuery } from "../../ducks/brokers";
import { useAddGroupFilterMutation } from "../../ducks/filter";
import { useGetGroupsQuery } from "../../ducks/groups";
import { useGetStreamsQuery } from "../../ducks/streams";
import SearchableValueSelect from "../SearchableValueSelect";

interface NewFilterDialogProps {
  open: boolean;
  onClose: () => void;
  brokerId?: number;
  groupId?: number;
  streamId?: number;
}

const NewFilterDialog = ({
  open,
  onClose,
  brokerId,
  groupId,
  streamId,
}: NewFilterDialogProps) => {
  const navigate = useNavigate();
  const [addGroupFilter] = useAddGroupFilterMutation();
  const { data: groups } = useGetGroupsQuery();
  const { data: streams } = useGetStreamsQuery();
  const { data: brokers = [] } = useGetBrokersQuery();

  const [name, setName] = useState("");
  const [selectedGroup, setSelectedGroup] = useState<number | "">("");
  const [selectedStream, setSelectedStream] = useState<number | "">("");
  const [selectedBroker, setSelectedBroker] = useState<number | "">("");
  const group = groupId ?? selectedGroup;
  const stream = streamId ?? selectedStream;
  const broker = brokerId ?? selectedBroker;
  const filterBrokers = brokers.filter(
    (b) => b.id === brokerId || (b.active && b.filter_kind !== "none"),
  );
  const incomplete =
    !name ||
    group === "" ||
    stream === "" ||
    (filterBrokers.length > 0 && broker === "");

  const onCreate = async (e: FormEvent) => {
    e.preventDefault();
    const { data } = await addGroupFilter({
      name,
      group_id: group,
      stream_id: stream,
      broker_id: broker || null,
    });
    if (data) navigate(`/filter/${data.id}`);
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <form onSubmit={onCreate}>
        <DialogTitle>New filter</DialogTitle>
        <DialogContent dividers>
          <Stack spacing={2}>
            <TextField
              autoFocus
              size="small"
              label="Name"
              name="filter_name"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            <SearchableValueSelect
              size="small"
              label="Group"
              options={groups?.userAccessible || []}
              value={group === "" ? null : group}
              disabled={groupId !== undefined}
              onChange={(id: number | null) => setSelectedGroup(id ?? "")}
            />
            <SearchableValueSelect
              size="small"
              label="Stream"
              options={(streams as { id: number; name: string }[]) || []}
              value={stream === "" ? null : stream}
              disabled={streamId !== undefined}
              onChange={(id: number | null) => setSelectedStream(id ?? "")}
            />
            {filterBrokers.length > 0 && (
              <TextField
                select
                size="small"
                label="Broker"
                value={broker}
                disabled={brokerId !== undefined}
                onChange={(e) => setSelectedBroker(Number(e.target.value))}
              >
                {filterBrokers.map((b) => (
                  <MenuItem key={b.id} value={b.id}>
                    {b.name}
                  </MenuItem>
                ))}
              </TextField>
            )}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Cancel</Button>
          <Button
            type="submit"
            variant="contained"
            disabled={incomplete}
            data-testid="add-filter-dialog-submit"
          >
            Create filter
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
};

export default NewFilterDialog;
