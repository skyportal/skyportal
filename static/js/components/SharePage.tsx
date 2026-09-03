import { useState } from "react";

import Dialog from "@mui/material/Dialog";
import IconButton from "@mui/material/IconButton";
import MobileScreenShareIcon from "@mui/icons-material/MobileScreenShare";
import { makeStyles } from "tss-react/mui";
import { QRCodeSVG } from "qrcode.react";

const useStyles = makeStyles()({
  paper: {
    fontWeight: "bold",
    fontSize: "150%",
    padding: "1rem",
  },
});

interface SharePageProps {
  value?: string | null;
}

const SharePage = ({ value = null }: SharePageProps) => {
  const { classes } = useStyles();

  const [open, setOpen] = useState(false);

  const handleOpen = () => {
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
  };

  // if a value is not provided, use the current page's URL
  let shareValue = value;
  if (shareValue === undefined || shareValue === null || shareValue === "") {
    shareValue = window.location.href;
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
        <QRCodeSVG value={shareValue} />
      </Dialog>
    </>
  );
};

export default SharePage;
