import React, { useState } from "react";
import PropTypes from "prop-types";
import makeStyles from "@mui/styles/makeStyles";
import Typography from "@mui/material/Typography";
import Popover from "@mui/material/Popover";
import IconButton from "@mui/material/IconButton";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";

const useStyles = makeStyles((theme) => ({
  header: {
    display: "flex",
    alignItems: "center",
    "& > h6": {
      marginRight: "0.5rem",
    },
  },
  title: {
    marginBottom: theme.spacing(1),
  },
  typography: {
    padding: theme.spacing(2),
  },
}));

const UserPreferencesHeader = ({ title, popupText, variant = "h6" }) => {
  const classes = useStyles();
  const [anchorEl, setAnchorEl] = useState(null);
  const handleClick = (event) => {
    setAnchorEl(event.currentTarget);
  };
  const handleClose = () => {
    setAnchorEl(null);
  };
  const open = Boolean(anchorEl);
  const id = open ? "simple-popover" : undefined;
  return (
    <div>
      <div className={classes.header}>
        <Typography
          variant={variant}
          display="inline"
          className={classes.title}
        >
          {title}
        </Typography>
        {popupText && (
          <IconButton aria-label="help" size="small" onClick={handleClick}>
            <HelpOutlineIcon />
          </IconButton>
        )}
      </div>
      <Popover
        id={id}
        open={open}
        anchorEl={anchorEl}
        onClose={handleClose}
        anchorOrigin={{
          vertical: "top",
          horizontal: "right",
        }}
        transformOrigin={{
          vertical: "top",
          horizontal: "left",
        }}
      >
        <Typography className={classes.typography}>{popupText}</Typography>
      </Popover>
    </div>
  );
};

UserPreferencesHeader.propTypes = {
  title: PropTypes.string.isRequired,
  popupText: PropTypes.string,
  variant: PropTypes.string,
};
UserPreferencesHeader.defaultProps = {
  popupText: null,
  variant: "h6",
};

export default UserPreferencesHeader;
