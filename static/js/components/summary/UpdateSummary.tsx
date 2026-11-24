import { useState } from "react";
import EditIcon from "@mui/icons-material/Edit";
import Chip from "@mui/material/Chip";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";

import Button from "../Button";
import EditDialog from "../source/EditDialog";

interface UpdateSummaryProps {
  summary?: string | null | undefined;
  summaryHistory?:
    { summary?: string | null; is_bot?: boolean }[] | null | undefined;
  showAISummaries?: boolean;
  chip?: boolean;
  onSave: (summary: string | null) => Promise<unknown>;
}

const UpdateSummary = ({
  summary,
  summaryHistory,
  showAISummaries = true,
  chip = false,
  onSave,
}: UpdateSummaryProps) => {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [text, setText] = useState("");
  const [saving, setSaving] = useState(false);

  const open = () => {
    setText(
      summaryHistory?.find(
        (s) => s.summary && (showAISummaries || s.is_bot === false),
      )?.summary ?? "",
    );
    setDialogOpen(true);
  };

  const save = async (value: string | null) => {
    setSaving(true);
    const saved = await onSave(value).then(
      () => true,
      () => false,
    );
    setSaving(false);
    if (saved) setDialogOpen(false);
  };

  return (
    <>
      {chip ? (
        <Chip
          size="small"
          variant="outlined"
          label="Add summary"
          onClick={open}
          data-testid="add-summary-button"
          sx={{
            borderStyle: "dashed",
            color: "text.secondary",
            "&:hover": { borderColor: "primary.main", color: "primary.main" },
          }}
        />
      ) : (
        <Tooltip title="Update Summary">
          <EditIcon
            fontSize="small"
            sx={{ height: "1rem", cursor: "pointer" }}
            onClick={open}
          />
        </Tooltip>
      )}
      <EditDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        title="Summary"
        maxWidth="sm"
        leftAction={
          summary && (
            <Button secondary disabled={saving} onClick={() => save(null)}>
              Clear
            </Button>
          )
        }
        actions={
          <Button
            primary
            disabled={saving || !text.trim()}
            onClick={() => save(text)}
          >
            Save
          </Button>
        }
      >
        <TextField
          size="small"
          value={text}
          minRows={4}
          maxRows={14}
          fullWidth
          multiline
          autoFocus
          onChange={(e) => setText(e.target.value)}
        />
      </EditDialog>
    </>
  );
};

export default UpdateSummary;
