import React, { useState } from "react";
import { useSelector, useDispatch } from "react-redux";

import FormGroup from "@material-ui/core/FormGroup";
import FormControlLabel from "@material-ui/core/FormControlLabel";
import Switch from "@material-ui/core/Switch";
import IconButton from "@material-ui/core/IconButton";
import TextField from "@material-ui/core/TextField";

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

const SlackPreferences = () => {
  const classes = useStyles();
  const profile = useSelector((state) => state.profile.preferences);
  const dispatch = useDispatch();

  const [anchorEl, setAnchorEl] = useState(null);
  const [slackurl, setSlackurl] = useState(profile.slack_integration?.url);
  const [slackurlerror, setSlackurlerror] = useState(false);

  const handleChange = (event) => {
    setSlackurl(event.target.value);
  };

  const handleBlur = () => {
    if (slackurl.startsWith("https://hooks.slack.com/")) {
      setSlackurlerror(false);
      const prefs = {
        slack_integration: {
          url: slackurl,
        },
      };
      dispatch(profileActions.updateUserPreferences(prefs));
    } else {
      setSlackurlerror(true);
    }
  };

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
      slack_integration: {
        [event.target.name]: event.target.checked,
      },
    };

    dispatch(profileActions.updateUserPreferences(prefs));
  };

  return (
    <div>
      <div className={classes.header}>
        <Typography variant="h6" display="inline">
          Slack Integration
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
          You&apos;ll need to ask your site administrator to give you a unique
          URL that posts to your Slack channel. Activating the Slack integration
          will allow you to see all @ mentions of this account and configure
          other notifications below.
        </Typography>
      </Popover>
      <FormGroup row>
        <FormControlLabel
          control={
            <Switch
              checked={profile.slack_integration?.active === true}
              name="active"
              onChange={prefToggled}
            />
          }
          label={profile.slack_integration?.active ? "Active" : "Inactive"}
        />
      </FormGroup>
      {profile.slack_integration?.active && (
        <div>
          <TextField
            name="url"
            label="Integration URL"
            fullWidth
            placeholder="Unique URL connecting to your Slack channel"
            defaultValue={profile.slack_integration?.url}
            onChange={handleChange}
            onBlur={handleBlur}
            margin="normal"
            helperText={
              slackurlerror ? "Must be a Slack URL" : "Valid Slack URL"
            }
            error={slackurlerror}
          />
        </div>
      )}
    </div>
  );
};

export default SlackPreferences;
