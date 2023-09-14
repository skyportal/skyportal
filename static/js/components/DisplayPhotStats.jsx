import React, { useState } from "react";
import { JSONTree } from "react-json-tree";
import PropTypes from "prop-types";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import VisibilityIcon from "@mui/icons-material/Visibility";

const DisplayPhotStats = ({ photstats, display_header }) => {
  const [dialogOpen, setDialogOpen] = useState(false);

  return (
    <div
      style={{ display: "flex", flexDirection: "row", alignItems: "center" }}
    >
      {display_header ? <b>Photometry Statistics: </b> : ""}
      <IconButton
        data-testid="showPhotStatsIcon"
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
        <DialogTitle>Photometry Statistics</DialogTitle>
        <DialogContent>
          <div>
            <JSONTree data={photstats} hideRoot />
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

DisplayPhotStats.propTypes = {
  photstats: PropTypes.shape(Object),
  display_header: PropTypes.bool,
};

DisplayPhotStats.defaultProps = {
  photstats: {},
  display_header: true,
};

export default DisplayPhotStats;
