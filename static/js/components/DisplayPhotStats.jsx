import React, { useState } from "react";
import { JSONTree } from "react-json-tree";
import PropTypes from "prop-types";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import AnalyticsIcon from "@mui/icons-material/Analytics";
import Tooltip from "@mui/material/Tooltip";

const DisplayPhotStats = ({ photstats, display_header }) => {
  const [dialogOpen, setDialogOpen] = useState(false);

  return (
    <div
      style={{ display: "flex", flexDirection: "row", alignItems: "center" }}
    >
      {display_header ? <b>Photometry Statistics:</b> : ""}
      <Tooltip title="Photometry Statistics">
        <IconButton
          data-testid="showPhotStatsIcon"
          size="small"
          onClick={(e) => {
            e.stopPropagation();
            setDialogOpen(true);
          }}
          style={{
            margin: 0,
            padding: 0,
            marginLeft: display_header ? "0.25rem" : 0,
          }}
        >
          <AnalyticsIcon />
        </IconButton>
      </Tooltip>
      <Dialog
        open={dialogOpen}
        onClose={(e) => {
          e.stopPropagation();
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
