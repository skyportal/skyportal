import React, { useState } from "react";

import Dialog from "@mui/material/Dialog";
import IconButton from "@mui/material/IconButton";
import MobileScreenShareIcon from "@mui/icons-material/MobileScreenShare";
import makeStyles from "@mui/styles/makeStyles";

import QRCode from "qrcode.react";

const useStyles = makeStyles({
  paper: {
    fontWeight: "bold",
    fontSize: "150%",
    padding: "1rem",
  },
});

const SharePage = () => {
  const classes = useStyles();

  const [open, setOpen] = useState(false);

  const handleOpen = () => {
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
  };

  const url = window.location.href;
  return (
    <>
      <IconButton
        color="inherit"
        aria-label="share page"
        onClick={handleOpen}
        edge="start"
        disableRipple
        size="large"
      >
        <MobileScreenShareIcon color="action" />
      </IconButton>
      <Dialog
        open={open}
        onClose={handleClose}
        classes={{
          paper: classes.paper,
        }}
      >
        <QRCode value={url} />
      </Dialog>
    </>
  );
};

export default SharePage;
