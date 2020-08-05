import React, { useState } from "react";

import Dialog from '@material-ui/core/Dialog';
import IconButton from '@material-ui/core/IconButton';
import MobileScreenShareIcon from '@material-ui/icons/MobileScreenShare';
import { makeStyles } from '@material-ui/core/styles';

import QRCode from 'qrcode.react';


const useStyles = makeStyles({
  paper: {
    fontWeight: 'bold',
    fontSize: '150%',
    padding: '1rem',
  }
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
      {
        !open &&
          (
            <IconButton
              color="inherit"
              aria-label="share page"
              onClick={handleOpen}
              edge="start"
            >
              <MobileScreenShareIcon color="action" />
            </IconButton>
          )
      }
      <Dialog
        open={open}
        onClose={handleClose}
        classes={{
          paper: classes.paper
        }}
      >
        <QRCode value={url} />
      </Dialog>
    </>
  );
};

export default SharePage;
