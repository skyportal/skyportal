import { useState } from "react";

import Box from "@mui/material/Box";
import Checkbox from "@mui/material/Checkbox";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import FormControlLabel from "@mui/material/FormControlLabel";
import TextField from "@mui/material/TextField";

import { useUpdateGroupMutation } from "../../ducks/groups";
import Button from "../Button";

const initialForm = (group: any) => ({
  name: group.name ?? "",
  nickname: group.nickname ?? "",
  description: group.description ?? "",
  private: group.private ?? false,
  auto_accept_requests: group.auto_accept_requests ?? false,
});

const GroupSettingsForm = ({ group }: { group: any }) => {
  const [updateGroup] = useUpdateGroupMutation();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(() => initialForm(group));

  const openDialog = () => {
    // Re-seed from the current group each time the dialog is opened.
    setForm(initialForm(group));
    setOpen(true);
  };

  const handleSubmit = async () => {
    try {
      await updateGroup({
        group_id: group.id,
        form_data: {
          name: form.name,
          // empty optional fields -> null (avoids a "" clash on the unique nickname)
          nickname: form.nickname || null,
          description: form.description || null,
          private: form.private,
          auto_accept_requests: form.auto_accept_requests,
        },
      }).unwrap();
      setOpen(false);
    } catch {
      // error notification handled by the API layer
    }
  };

  return (
    <>
      <Button secondary onClick={openDialog} data-testid="editGroupButton">
        Edit Group
      </Button>
      <Dialog fullWidth open={open} onClose={() => setOpen(false)}>
        <DialogTitle>Edit Group</DialogTitle>
        <DialogContent dividers>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2, mt: 1 }}>
            <TextField
              label="Group Name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
            <TextField
              label="Nickname"
              value={form.nickname}
              onChange={(e) => setForm({ ...form, nickname: e.target.value })}
            />
            <TextField
              label="Description"
              value={form.description}
              onChange={(e) =>
                setForm({ ...form, description: e.target.value })
              }
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={form.private}
                  onChange={(e) =>
                    setForm({ ...form, private: e.target.checked })
                  }
                />
              }
              label="Private (invisible to non-members)"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={form.auto_accept_requests}
                  onChange={(e) =>
                    setForm({ ...form, auto_accept_requests: e.target.checked })
                  }
                  data-testid="editAutoAcceptRequestsCheckbox"
                />
              }
              label="Automatically accept requests to join this group"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button secondary onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button
            primary
            onClick={handleSubmit}
            data-testid="submitEditGroupButton"
          >
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default GroupSettingsForm;
