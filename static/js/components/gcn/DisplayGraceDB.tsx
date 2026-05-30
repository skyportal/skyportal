import React, { useState } from "react";
import { JSONTree } from "react-json-tree";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import VisibilityIcon from "@mui/icons-material/Visibility";

interface DisplayGraceDBProps {
  gcnEvent: {
    gracedb_labels?: Record<string, any>;
    gracedb_log?: Record<string, any>;
  };
  display_header?: boolean;
}

const DisplayGraceDB = ({
  gcnEvent,
  display_header = true,
}: DisplayGraceDBProps) => {
  const [dialogOpen, setDialogOpen] = useState(false);

  return (
    <>
      {display_header ? <b>GraceDB Messages: </b> : ""}
      <IconButton
        data-testid="showGraceDBMessagesIcon"
        size="small"
        onClick={() => {
          setDialogOpen(true);
        }}
      >
        <VisibilityIcon />
      </IconButton>
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)}>
        <DialogTitle>Labels</DialogTitle>
        <DialogContent>
          <div>
            <JSONTree data={gcnEvent.gracedb_labels} hideRoot />
          </div>
        </DialogContent>
        <DialogTitle>Logs</DialogTitle>
        <DialogContent>
          <div>
            <JSONTree data={gcnEvent.gracedb_log} hideRoot />
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default DisplayGraceDB;
