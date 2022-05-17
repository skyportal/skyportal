import React, { useState } from "react";
import PropTypes from "prop-types";
import { makeStyles } from "@material-ui/core/styles";
import Typography from "@material-ui/core/Typography";
import Popover from "@material-ui/core/Popover";
import IconButton from "@material-ui/core/IconButton";
import HelpOutlineIcon from "@material-ui/icons/HelpOutline";

const useStyles = makeStyles((theme) => ({
  header: {
    display: "flex",
    alignItems: "center",
    "& > h6": {
      marginRight: "0.5rem",
    },
  },
  typography: {
    padding: theme.spacing(2),
  },
}));

const UserPreferencesHeader = ({ title, popupText }) => {
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
        <Typography variant="h6" display="inline">
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
};
UserPreferencesHeader.defaultProps = {
  popupText: null,
};

export default UserPreferencesHeader;
