import React, { useState } from "react";
import { JSONTree } from "react-json-tree";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import VisibilityIcon from "@mui/icons-material/Visibility";

interface DisplayTNSInfoProps {
  tns_info?: any;
  display_header?: boolean;
}

const DisplayTNSInfo = ({
  tns_info = {},
  display_header = true,
}: DisplayTNSInfoProps) => {
  const [dialogOpen, setDialogOpen] = useState(false);

  return (
    <>
      {display_header ? <b>TNS Info: </b> : ""}
      <IconButton
        data-testid="showTNSInfoIcon"
        size="small"
        onClick={() => {
          setDialogOpen(true);
        }}
      >
        <VisibilityIcon />
      </IconButton>
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)}>
        <DialogTitle>TNS Info</DialogTitle>
        <DialogContent>
          <div>
            <JSONTree data={tns_info} hideRoot />
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default DisplayTNSInfo;
