import { useState } from "react";

import Button from "@mui/material/Button";
import Checkbox from "@mui/material/Checkbox";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import FormControlLabel from "@mui/material/FormControlLabel";
import FormGroup from "@mui/material/FormGroup";

import { showNotification } from "baselayer/components/Notifications";

import { useAppDispatch } from "../../types/hooks";
import { useGetGroupsQuery } from "../../ducks/groups";
import { useSaveBrokerAlertAsSourceMutation } from "../../ducks/brokers";

interface BrokerSaveButtonProps {
  brokerId: number;
  objectId: string;
}

const BrokerSaveButton = ({ brokerId, objectId }: BrokerSaveButtonProps) => {
  const dispatch = useAppDispatch();
  const { data: groups } = useGetGroupsQuery();
  const [saveAlert, { isLoading }] = useSaveBrokerAlertAsSourceMutation();

  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState<number[]>([]);

  const accessible = (groups as any)?.userAccessible ?? [];

  const toggle = (id: number) =>
    setSelected((s) =>
      s.includes(id) ? s.filter((x) => x !== id) : [...s, id],
    );

  const onSave = async () => {
    const res: any = await saveAlert({
      brokerId,
      alertId: objectId,
      groupIds: selected,
    });
    if (res?.data) {
      dispatch(showNotification(`Saved ${objectId} as a source`));
      setOpen(false);
    } else {
      const msg = res?.error?.data?.message ?? "Error saving as source";
      dispatch(showNotification(msg, "error"));
    }
  };

  return (
    <>
      <Button size="small" variant="outlined" onClick={() => setOpen(true)}>
        Save as source
      </Button>
      <Dialog open={open} onClose={() => setOpen(false)}>
        <DialogTitle>{`Save ${objectId} to groups`}</DialogTitle>
        <DialogContent>
          <FormGroup>
            {accessible.map((g: any) => (
              <FormControlLabel
                key={g.id}
                control={
                  <Checkbox
                    checked={selected.includes(g.id)}
                    onChange={() => toggle(g.id)}
                  />
                }
                label={g.name}
              />
            ))}
          </FormGroup>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            disabled={selected.length === 0 || isLoading}
            onClick={onSave}
          >
            {isLoading ? "Saving…" : "Save"}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default BrokerSaveButton;
