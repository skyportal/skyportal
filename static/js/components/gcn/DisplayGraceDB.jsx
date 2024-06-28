import React, { useState } from "react";
import { JSONTree } from "react-json-tree";
import PropTypes from "prop-types";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import VisibilityIcon from "@mui/icons-material/Visibility";

const DisplayGraceDB = ({ gcnEvent, display_header }) => {
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
      <Dialog
        open={dialogOpen}
        onClose={() => {
          setDialogOpen(false);
        }}
        style={{ position: "fixed" }}
      >
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

DisplayGraceDB.propTypes = {
  gcnEvent: PropTypes.shape({
    gracedb_labels: PropTypes.shape(Object),
    gracedb_log: PropTypes.shape(Object),
  }).isRequired,
  display_header: PropTypes.bool,
};

DisplayGraceDB.defaultProps = {
  display_header: true,
};

export default DisplayGraceDB;
