import { useState } from "react";

import Box from "@mui/material/Box";
import Checkbox from "@mui/material/Checkbox";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import FormControlLabel from "@mui/material/FormControlLabel";
import IconButton from "@mui/material/IconButton";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import EditIcon from "@mui/icons-material/Edit";

import { useUpdateGroupMutation } from "../../ducks/groups";
import Button from "../Button";

const initialForm = (group: any) => ({
  name: group.name ?? "",
  nickname: group.nickname ?? "",
  description: group.description ?? "",
  private: group.private ?? false,
  auto_accept_requests: group.auto_accept_requests ?? false,
  discoverable_data: group.discoverable_data ?? true,
});

const TEXT_FIELDS = [
  { field: "name", label: "Group Name" },
  { field: "nickname", label: "Nickname" },
  { field: "description", label: "Description" },
] as const;

const CHECKBOXES = [
  {
    field: "private",
    label: "Private (invisible to non-members)",
    testId: undefined,
  },
  {
    field: "auto_accept_requests",
    label: "Automatically accept requests to join this group",
    testId: "editAutoAcceptRequestsCheckbox",
  },
  {
    field: "discoverable_data",
    label: "Let non-members see that this group's data exists, and ask for it",
    testId: "editDiscoverableDataCheckbox",
  },
] as const;

const GroupSettingsForm = ({ group }: { group: any }) => {
  const [updateGroup] = useUpdateGroupMutation();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(() => initialForm(group));

  const openDialog = () => {
    setForm(initialForm(group));
    setOpen(true);
  };

  const handleSubmit = async () => {
    const { error } = await updateGroup({
      group_id: group.id,
      form_data: {
        ...form,
        // empty optional fields -> null (avoids a "" clash on the unique nickname)
        nickname: form.nickname || null,
        description: form.description || null,
      },
    });
    if (!error) setOpen(false);
  };

  return (
    <>
      <Tooltip title="Edit group">
        <IconButton onClick={openDialog} data-testid="editGroupButton">
          <EditIcon />
        </IconButton>
      </Tooltip>
      <Dialog fullWidth open={open} onClose={() => setOpen(false)}>
        <DialogTitle>Edit Group</DialogTitle>
        <DialogContent dividers>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2, mt: 1 }}>
            {TEXT_FIELDS.map(({ field, label }) => (
              <TextField
                key={field}
                label={label}
                value={form[field]}
                onChange={(e) => setForm({ ...form, [field]: e.target.value })}
              />
            ))}
            {CHECKBOXES.map(({ field, label, testId }) => (
              <FormControlLabel
                key={field}
                control={
                  <Checkbox
                    checked={form[field]}
                    onChange={(e) =>
                      setForm({ ...form, [field]: e.target.checked })
                    }
                    data-testid={testId}
                  />
                }
                label={label}
              />
            ))}
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
