import React, { useEffect, useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import FormGroup from "@mui/material/FormGroup";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";
import { withStyles, makeStyles } from "@mui/styles";
import PropTypes from "prop-types";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import MuiDialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import Close from "@mui/icons-material/Close";
import Typography from "@mui/material/Typography";
import Tooltip from "@mui/material/Tooltip";
import grey from "@mui/material/colors/grey";
import EditNotificationsIcon from "@mui/icons-material/EditNotifications";
import HelpOutlineOutlinedIcon from "@mui/icons-material/HelpOutlineOutlined";
import { Box, Slider, Checkbox, Button } from "@mui/material";
import * as profileActions from "../ducks/profile";

const useStyles = makeStyles((theme) => ({
  typography: {
    padding: theme.spacing(2),
  },
  pref: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "left",
    alignItems: "center",
    gap: "10px",
    width: "60rem",
    height: "5rem",
  },
  options: {
    marginLeft: "4rem",
    display: "flex",
    flexDirection: "row",
    justifyContent: "left",
    alignItems: "center",
    gap: "10px",
    width: "60rem",
    height: "4rem",
  },
  form_group: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "left",
    alignItems: "center",
  },
  button: {
    height: "3rem",
  },
  tooltip: {
    fontSize: "1rem",
    maxWidth: "30rem",
  },
}));

const dialogTitleStyles = (theme) => ({
  root: {
    margin: 0,
    padding: theme.spacing(2),
  },
  title: {
    marginRight: theme.spacing(2),
  },
  closeButton: {
    position: "absolute",
    right: theme.spacing(1),
    top: theme.spacing(1),
    color: grey[500],
  },
});

const DialogTitle = withStyles(dialogTitleStyles)(
  ({ children, classes, onClose }) => (
    <MuiDialogTitle disableTypography className={classes.root}>
      <Typography variant="h6" className={classes.title}>
        {children}
      </Typography>
      {onClose ? (
        <IconButton
          aria-label="close"
          className={classes.closeButton}
          onClick={onClose}
        >
          <Close />
        </IconButton>
      ) : null}
    </MuiDialogTitle>
  )
);

const NotificationSettingsSelect = ({ notificationResourceType }) => {
  const classes = useStyles();
  const [open, setOpen] = useState(false);
  const profile = useSelector((state) => state.profile.preferences);
  const dispatch = useDispatch();
  const [value, setValue] = React.useState();
  const [inverted, setInverted] = React.useState(false);

  useEffect(() => {
    if (!value) {
      const val =
        profile?.notifications[notificationResourceType]?.sms?.time_slot;
      if (val?.length > 0) {
        setValue(val);
        if (val[0] > val[1]) {
          setInverted(true);
        }
      }
    }
  }, [profile]);

  const handleClose = () => {
    setOpen(false);
  };

  const prefToggled = (event) => {
    if (
      notificationResourceType === "gcn_events" ||
      notificationResourceType === "sources" ||
      notificationResourceType === "favorite_sources" ||
      notificationResourceType === "facility_transactions" ||
      notificationResourceType === "mention"
    ) {
      const prefs = {
        notifications: {
          [notificationResourceType]: {},
        },
      };
      if (event.target.name === "on_shift") {
        prefs.notifications[notificationResourceType].sms = {};
        prefs.notifications[notificationResourceType].sms[event.target.name] =
          event.target.checked;
      } else if (event.target.name === "time_slot") {
        prefs.notifications[notificationResourceType].sms = {};
        if (event.target.checked) {
          prefs.notifications[notificationResourceType].sms[event.target.name] =
            [8, 20];
          setValue([8, 20]);
        } else {
          prefs.notifications[notificationResourceType].sms[event.target.name] =
            [];
          setValue([]);
        }
      } else {
        prefs.notifications[notificationResourceType][event.target.name] = {
          active: event.target.checked,
        };
      }

      dispatch(profileActions.updateUserPreferences(prefs));
    }
  };

  const onChangeInverted = () => {
    if (
      notificationResourceType === "gcn_events" ||
      notificationResourceType === "sources" ||
      notificationResourceType === "favorite_sources" ||
      notificationResourceType === "facility_transactions" ||
      notificationResourceType === "mention"
    ) {
      const prefs = {
        notifications: {
          [notificationResourceType]: {
            sms: {
              time_slot: value.reverse(),
            },
          },
        },
      };

      dispatch(profileActions.updateUserPreferences(prefs));
    }
    setValue(value.reverse());
    setInverted(!inverted);
  };

  const handleChecked = (type) => {
    let checked = false;
    if (type === "on_shift") {
      checked = profile?.notifications[notificationResourceType]?.sms?.on_shift;
    } else if (type === "time_slot") {
      checked =
        profile?.notifications[notificationResourceType]?.sms?.time_slot
          ?.length > 0;
    } else {
      checked = profile?.notifications[notificationResourceType][type]?.active;
    }
    return checked;
  };

  const valuetext = (val) => `${val}H`;
  const handleChange = (event, newValue) => {
    setValue(newValue);
  };

  const handleChangeCommitted = () => {
    if (
      notificationResourceType === "gcn_events" ||
      notificationResourceType === "sources" ||
      notificationResourceType === "favorite_sources" ||
      notificationResourceType === "facility_transactions" ||
      notificationResourceType === "mention"
    ) {
      const prefs = {
        notifications: {
          [notificationResourceType]: {
            sms: {
              [`time_slot`]: value,
            },
          },
        },
      };

      dispatch(profileActions.updateUserPreferences(prefs));
    }
  };

  return (
    <div>
      <Tooltip
        title="Click here to open the notification settings. There, you can choose if you want to be also notified by email, sms and/or slack for the selected notification type."
        placement="right"
        classes={{ tooltip: classes.tooltip }}
      >
        <Button
          variant="contained"
          name={`notification_settings_button_${notificationResourceType}`}
          className={classes.button}
          onClick={() => {
            setOpen(true);
          }}
        >
          <EditNotificationsIcon />
        </Button>
      </Tooltip>
      {open && (
        <Dialog
          open={open}
          onClose={handleClose}
          style={{ position: "fixed" }}
          maxWidth="md"
        >
          <DialogTitle onClose={handleClose}>Notification Settings</DialogTitle>
          <DialogContent dividers>
            <div className={classes.dialogContent}>
              <div className={classes.pref}>
                <FormGroup row className={classes.form_group}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={handleChecked("email")}
                        name="email"
                        onChange={prefToggled}
                      />
                    }
                    label="By Email"
                  />
                  <Tooltip
                    title="Click here to receive notifications by email about the selected notification type. You also need to set your email address in your user profile."
                    placement="right"
                    classes={{ tooltip: classes.tooltip }}
                  >
                    <HelpOutlineOutlinedIcon />
                  </Tooltip>
                </FormGroup>
              </div>
              <div className={classes.pref}>
                <FormGroup row className={classes.form_group}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={handleChecked("slack")}
                        name="slack"
                        onChange={prefToggled}
                      />
                    }
                    label="Message on Slack"
                  />
                  <Tooltip
                    title="Click here to receive notifications on Slack about the selected notification type. You also need to active the Slack integration and set the slack url in your user profile."
                    placement="right"
                    classes={{ tooltip: classes.tooltip }}
                  >
                    <HelpOutlineOutlinedIcon />
                  </Tooltip>
                </FormGroup>
              </div>
              <div className={classes.pref}>
                <FormGroup row className={classes.form_group}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={handleChecked("sms")}
                        name="sms"
                        onChange={prefToggled}
                      />
                    }
                    label=" By SMS"
                  />
                  <Tooltip
                    title="Click here to receive notifications by SMS about the selected notification type. You also need to set your phone number in your user profile. Two options will appear, please select at least one."
                    placement="right"
                    classes={{ tooltip: classes.tooltip }}
                  >
                    <HelpOutlineOutlinedIcon />
                  </Tooltip>
                </FormGroup>
              </div>
              {profile?.notifications?.[notificationResourceType]?.sms
                ?.active && (
                <div className={classes.options}>
                  <FormGroup row className={classes.form_group}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={handleChecked("on_shift")}
                          name="on_shift"
                          onChange={prefToggled}
                        />
                      }
                      label="On Shift"
                    />
                    <Tooltip
                      title="Click here to receive notifications by SMS when you are on shift. This is in addition to the time slot option. "
                      placement="right"
                      classes={{ tooltip: classes.tooltip }}
                    >
                      <HelpOutlineOutlinedIcon />
                    </Tooltip>
                  </FormGroup>
                  <FormGroup row className={classes.form_group}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={handleChecked("time_slot")}
                          name="time_slot"
                          onChange={prefToggled}
                        />
                      }
                      label="Time Slot (UTC)"
                    />
                    <Tooltip
                      title="Click here to receive notifications by SMS during a specific time slot. Outside of the time slot, you will not receive any messages on your phone. This is in addition to notifications during shifts, if configured."
                      placement="right"
                      classes={{ tooltip: classes.tooltip }}
                    >
                      <HelpOutlineOutlinedIcon />
                    </Tooltip>
                  </FormGroup>
                  {profile?.notifications?.[notificationResourceType]?.sms
                    ?.time_slot?.length > 0 && (
                    <Box
                      sx={{ width: 300 }}
                      display="flex"
                      flexDirection="row"
                      alignItems="center"
                    >
                      <Slider
                        getAriaLabel={() => "time_slot_slider"}
                        value={value}
                        onChange={handleChange}
                        onChangeCommitted={handleChangeCommitted}
                        valueLabelDisplay="on"
                        getAriaValueText={valuetext}
                        min={0}
                        max={24}
                        step={1}
                        marks
                        track={inverted ? "inverted" : "normal"}
                      />
                      <Checkbox
                        checked={inverted === true}
                        onChange={() => onChangeInverted()}
                        label="Invert"
                      />
                      <Tooltip
                        title="Select a start and end time on the slider. If you want to receive notifications outside and not inside the time slot, check the Invert option."
                        placement="right"
                        classes={{ tooltip: classes.tooltip }}
                      >
                        <HelpOutlineOutlinedIcon />
                      </Tooltip>
                    </Box>
                  )}
                </div>
              )}
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
};

NotificationSettingsSelect.propTypes = {
  notificationResourceType: PropTypes.string,
};

NotificationSettingsSelect.defaultProps = {
  notificationResourceType: "",
};

export default NotificationSettingsSelect;
