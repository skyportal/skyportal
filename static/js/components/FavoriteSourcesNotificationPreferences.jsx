import React, { useState } from "react";
import { useSelector, useDispatch } from "react-redux";

import FormGroup from "@material-ui/core/FormGroup";
import FormControlLabel from "@material-ui/core/FormControlLabel";
import Switch from "@material-ui/core/Switch";
import IconButton from "@material-ui/core/IconButton";
import HelpOutlineIcon from "@material-ui/icons/HelpOutline";
import Typography from "@material-ui/core/Typography";
import { makeStyles } from "@material-ui/core/styles";
import Popover from "@material-ui/core/Popover";

import * as profileActions from "../ducks/profile";

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

const FavoriteSourcesNotificationPreferences = () => {
  const classes = useStyles();
  const profile = useSelector((state) => state.profile.preferences);
  const dispatch = useDispatch();

  const [anchorEl, setAnchorEl] = useState(null);
  const handleClick = (event) => {
    setAnchorEl(event.currentTarget);
  };
  const handleClose = () => {
    setAnchorEl(null);
  };
  const open = Boolean(anchorEl);
  const id = open ? "simple-popover" : undefined;

  const prefToggled = (event) => {
    const prefs = {
      favorite_sources_activity_notifications: {
        [event.target.name]: event.target.checked,
      },
    };

    dispatch(profileActions.updateUserPreferences(prefs));
  };

  return (
    <div>
      <div className={classes.header}>
        <Typography variant="h6" display="inline">
          Browser Notifications For Favorite Source Activity
        </Typography>
        <IconButton aria-label="help" size="small" onClick={handleClick}>
          <HelpOutlineIcon />
        </IconButton>
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
        <Typography className={classes.typography}>
          Enable these to receive browser notifications for the selected
          activity types regarding sources you have starred/favorited.
        </Typography>
      </Popover>
      <FormGroup row>
        <FormControlLabel
          control={
            <Switch
              checked={
                profile.favorite_sources_activity_notifications?.comments ===
                true
              }
              name="comments"
              onChange={prefToggled}
            />
          }
          label="New Comments"
        />
        <FormControlLabel
          control={
            <Switch
              checked={
                profile.favorite_sources_activity_notifications?.spectra ===
                true
              }
              name="spectra"
              onChange={prefToggled}
            />
          }
          label="New Spectra"
        />
        <FormControlLabel
          control={
            <Switch
              checked={
                profile.favorite_sources_activity_notifications
                  ?.classifications === true
              }
              name="classifications"
              onChange={prefToggled}
            />
          }
          label="New Classifications"
        />
      </FormGroup>
    </div>
  );
};

export default FavoriteSourcesNotificationPreferences;
