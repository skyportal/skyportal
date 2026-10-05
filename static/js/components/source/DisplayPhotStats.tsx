import { useState } from "react";
import type { MouseEvent } from "react";
import { JSONTree } from "react-json-tree";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import AnalyticsIcon from "@mui/icons-material/Analytics";
import Tooltip from "@mui/material/Tooltip";

interface DisplayPhotStatsProps {
  photstats?: Record<string, any>;
}

const DisplayPhotStats = ({ photstats = {} }: DisplayPhotStatsProps) => {
  const [dialogOpen, setDialogOpen] = useState(false);
  const open = (event: MouseEvent) => {
    event.stopPropagation();
    setDialogOpen(true);
  };

  return (
    <>
      <Tooltip title="Photometry statistics">
        <IconButton
          size="small"
          onClick={open}
          data-testid="showPhotStatsIcon"
          sx={{ p: 0 }}
        >
          <AnalyticsIcon />
        </IconButton>
      </Tooltip>
      <Dialog
        open={dialogOpen}
        onClose={(event: any) => {
          event.stopPropagation();
          setDialogOpen(false);
        }}
      >
        <DialogTitle>Photometry Statistics</DialogTitle>
        <DialogContent>
          <JSONTree data={photstats} hideRoot />
        </DialogContent>
      </Dialog>
    </>
  );
};

export default DisplayPhotStats;
