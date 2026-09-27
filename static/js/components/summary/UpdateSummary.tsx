import { useState } from "react";
import EditIcon from "@mui/icons-material/Edit";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";

interface UpdateSummaryProps {
  summary?: string | null | undefined;
  summaryHistory?:
    { summary?: string | null; is_bot?: boolean }[] | null | undefined;
  showAISummaries?: boolean;
  onSave: (summary: string | null) => Promise<unknown>;
}

const UpdateSummary = ({
  summary,
  summaryHistory,
  showAISummaries = true,
  onSave,
}: UpdateSummaryProps) => {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [text, setText] = useState("");
  const [saving, setSaving] = useState(false);

  const openDialog = () => {
    const latest = (summaryHistory ?? []).find(
      (s) => s?.summary && (showAISummaries || s.is_bot === false),
    );
    setText(latest?.summary ?? "");
    setDialogOpen(true);
  };

  const save = async (value: string | null) => {
    setSaving(true);
    try {
      await onSave(value);
      setDialogOpen(false);
    } catch {
      // error notification handled by the baseQuery
    }
    setSaving(false);
  };

  return (
    <>
      <Tooltip title="Update Summary">
        <EditIcon
          fontSize="small"
          sx={{ height: "1rem", cursor: "pointer" }}
          onClick={openDialog}
        />
      </Tooltip>
      <Dialog
        open={dialogOpen}
        fullWidth
        maxWidth="lg"
        onClose={() => setDialogOpen(false)}
      >
        <DialogTitle>Update Summary</DialogTitle>
        <DialogContent dividers>
          <TextField
            size="small"
            label="Summary"
            value={text}
            minRows={2}
            fullWidth
            multiline
            error={!text.trim()}
            helperText={!text.trim() && "Please enter a valid summary"}
            onChange={(e) => setText(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Tooltip title="Clear the summary (set to null)">
            <Box component="span" sx={{ mr: "auto" }}>
              <Button
                color="error"
                disabled={saving || !summary}
                onClick={() => save(null)}
              >
                Clear
              </Button>
            </Box>
          </Tooltip>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            disabled={saving || !text.trim()}
            onClick={() => save(text)}
          >
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default UpdateSummary;
