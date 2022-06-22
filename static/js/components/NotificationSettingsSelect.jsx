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
import grey from "@mui/material/colors/grey";
import NotificationsActiveOutlined from "@mui/icons-material/NotificationsActiveOutlined";
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
  button: {
    height: "3rem",
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

const NotificationSettingsSelect = ({ notificationRessourceType }) => {
  const classes = useStyles();
  const [open, setOpen] = useState(false);
  const profile = useSelector((state) => state.profile.preferences);
  const dispatch = useDispatch();
  const [value, setValue] = React.useState();
  const [inverted, setInverted] = React.useState(false);

  useEffect(() => {
    if (!value) {
      const val =
        profile?.notifications[notificationRessourceType]?.sms?.time_slot;
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
      notificationRessourceType === "gcn_events" ||
      notificationRessourceType === "sources" ||
      notificationRessourceType === "favorite_sources" ||
      notificationRessourceType === "facility_transactions" ||
      notificationRessourceType === "mention"
    ) {
      const prefs = {
        notifications: {
          [notificationRessourceType]: {},
        },
      };
      if (event.target.name === "on_shift") {
        prefs.notifications[notificationRessourceType].sms = {};
        prefs.notifications[notificationRessourceType].sms[event.target.name] =
          event.target.checked;
      } else if (event.target.name === "time_slot") {
        prefs.notifications[notificationRessourceType].sms = {};
        if (event.target.checked) {
          prefs.notifications[notificationRessourceType].sms[
            event.target.name
          ] = [8, 20];
          setValue([8, 20]);
        } else {
          prefs.notifications[notificationRessourceType].sms[
            event.target.name
          ] = [];
          setValue([]);
        }
      } else {
        prefs.notifications[notificationRessourceType][event.target.name] = {
          active: event.target.checked,
        };
      }

      dispatch(profileActions.updateUserPreferences(prefs));
    }
  };

  const onChangeInverted = () => {
    if (
      notificationRessourceType === "gcn_events" ||
      notificationRessourceType === "sources" ||
      notificationRessourceType === "favorite_sources" ||
      notificationRessourceType === "facility_transactions" ||
      notificationRessourceType === "mention"
    ) {
      const prefs = {
        notifications: {
          [notificationRessourceType]: {
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
      checked =
        profile?.notifications[notificationRessourceType]?.sms?.on_shift;
    } else if (type === "time_slot") {
      checked =
        profile?.notifications[notificationRessourceType]?.sms?.time_slot
          ?.length > 0;
    } else {
      checked = profile?.notifications[notificationRessourceType][type]?.active;
    }
    return checked;
  };

  const valuetext = (val) => `${val}H`;
  const handleChange = (event, newValue) => {
    setValue(newValue);
  };

  const handleChangeCommitted = () => {
    if (
      notificationRessourceType === "gcn_events" ||
      notificationRessourceType === "sources" ||
      notificationRessourceType === "favorite_sources" ||
      notificationRessourceType === "facility_transactions" ||
      notificationRessourceType === "mention"
    ) {
      const prefs = {
        notifications: {
          [notificationRessourceType]: {
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
      <Button
        variant="contained"
        name={`notification_settings_button_${notificationRessourceType}`}
        className={classes.button}
        onClick={() => {
          setOpen(true);
        }}
      >
        <NotificationsActiveOutlined />
      </Button>
      {open && (
        <Dialog
          open={open}
          onClose={handleClose}
          style={{ position: "fixed" }}
          maxWidth="md"
        >
          <DialogTitle onClose={handleClose}>Notification Type</DialogTitle>
          <DialogContent dividers>
            <div className={classes.dialogContent}>
              <div className={classes.pref}>
                <FormGroup row>
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
                </FormGroup>
              </div>
              <div className={classes.pref}>
                <FormGroup row>
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
                </FormGroup>
              </div>
              <div className={classes.pref}>
                <FormGroup row>
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
                </FormGroup>
              </div>
              {profile?.notifications?.[notificationRessourceType]?.sms
                ?.active && (
                <div className={classes.options}>
                  <FormGroup row>
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
                  </FormGroup>
                  <FormGroup row>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={handleChecked("time_slot")}
                          name="time_slot"
                          onChange={prefToggled}
                        />
                      }
                      label="Time Slot"
                    />
                  </FormGroup>
                  {profile?.notifications?.[notificationRessourceType]?.sms
                    ?.time_slot?.length > 0 && (
                    <Box
                      sx={{ width: 300 }}
                      display="flex"
                      flexDirection="row"
                      alignItems="center"
                    >
                      <Slider
                        getAriaLabel={() => "Time Slot"}
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
  notificationRessourceType: PropTypes.string,
};

NotificationSettingsSelect.defaultProps = {
  notificationRessourceType: "",
};

export default NotificationSettingsSelect;
