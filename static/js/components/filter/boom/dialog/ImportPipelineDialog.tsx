import { useState } from "react";
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  TextField,
} from "@mui/material";

import { isRawMongoPipeline } from "../pipelineFormat";

interface ImportPipelineDialogProps {
  open: boolean;
  onClose: () => void;
  onImport: (pipeline: any[]) => void;
}

const ImportPipelineDialog = ({
  open,
  onClose,
  onImport,
}: ImportPipelineDialogProps) => {
  const [text, setText] = useState("");
  const [error, setError] = useState("");

  const handleClose = () => {
    setText("");
    setError("");
    onClose();
  };

  const handleImport = () => {
    let pipeline;
    try {
      pipeline = JSON.parse(text);
    } catch (e: any) {
      setError(`Invalid JSON: ${e.message}`);
      return;
    }
    if (!isRawMongoPipeline(pipeline)) {
      setError(
        'Expected a MongoDB aggregation pipeline: a list of stages such as [{"$match": {...}}].',
      );
      return;
    }
    onImport(pipeline);
    handleClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} fullWidth maxWidth="md">
      <DialogTitle>Import JSON</DialogTitle>
      <DialogContent>
        <DialogContentText>
          Paste a MongoDB aggregation pipeline. It becomes blocks when the
          builder can show it, and stays read-only otherwise. Nothing is saved
          until you click Save.
        </DialogContentText>
        <TextField
          autoFocus
          multiline
          fullWidth
          minRows={12}
          maxRows={24}
          margin="dense"
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            setError("");
          }}
          error={!!error}
          helperText={error || " "}
          placeholder='[{"$match": {"candidate.drb": {"$gt": 0.9}}}]'
          sx={{ "& textarea": { fontFamily: "monospace", fontSize: "0.8rem" } }}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>Cancel</Button>
        <Button
          onClick={handleImport}
          variant="contained"
          disabled={!text.trim()}
        >
          Import
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ImportPipelineDialog;
