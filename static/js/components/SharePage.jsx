import React, { useState } from "react";
import PropTypes from "prop-types";

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

const SharePage = ({ value }) => {
  const classes = useStyles();

  const [open, setOpen] = useState(false);

  const handleOpen = () => {
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
  };

  // if a value is not provided, use the current page's URL
  if (value === undefined || value === null || value === "") {
    value = window.location.href;
  }

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
        <QRCode value={value} />
      </Dialog>
    </>
  );
};

SharePage.propTypes = {
  value: PropTypes.string,
};

SharePage.defaultProps = {
  value: null,
};

export default SharePage;
