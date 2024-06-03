import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import FormGroup from "@mui/material/FormGroup";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";
import { makeStyles, withStyles } from "@mui/styles";
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
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Checkbox from "@mui/material/Checkbox";
import Slider from "@mui/material/Slider";
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
  ),
);

const NotificationSettingsSelect = ({ notificationResourceType }) => {
  const classes = useStyles();
  const [open, setOpen] = useState(false);
  const profile = useSelector((state) => state.profile.preferences);
  const dispatch = useDispatch();
  const [valueSMS, setValueSMS] = useState();
  const [invertedSMS, setInvertedSMS] = useState(false);
  const [valuePhone, setValuePhone] = useState();
  const [invertedPhone, setInvertedPhone] = useState(false);
  const [valueWhatsapp, setValueWhatsapp] = useState();
  const [invertedWhatsapp, setInvertedWhatsapp] = useState(false);

  useEffect(() => {
    if (!valueSMS) {
      const valSMS =
        profile?.notifications[notificationResourceType]?.sms?.time_slot;
      if (valSMS?.length > 0) {
        setValueSMS(valSMS);
        if (valSMS[0] > valSMS[1]) {
          setInvertedSMS(true);
        }
      }
    }
    if (!valuePhone) {
      const valPhone =
        profile?.notifications[notificationResourceType]?.phone?.time_slot;
      if (valPhone?.length > 0) {
        setValuePhone(valPhone);
        if (valPhone[0] > valPhone[1]) {
          setInvertedPhone(true);
        }
      }
    }
    if (!valueWhatsapp) {
      const valWhatsapp =
        profile?.notifications[notificationResourceType]?.whatsapp?.time_slot;
      if (valWhatsapp?.length > 0) {
        setValueWhatsapp(valWhatsapp);
        if (valWhatsapp[0] > valWhatsapp[1]) {
          setInvertedWhatsapp(true);
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
      notificationResourceType === "mention" ||
      notificationResourceType === "analysis_services" ||
      notificationResourceType === "observation_plans"
    ) {
      const prefs = {
        notifications: {
          [notificationResourceType]: {},
        },
      };
      if (event.target.name === "on_shift_sms") {
        prefs.notifications[notificationResourceType].sms = {};
        prefs.notifications[notificationResourceType].sms.on_shift =
          event.target.checked;
      } else if (event.target.name === "time_slot_sms") {
        prefs.notifications[notificationResourceType].sms = {};
        if (event.target.checked) {
          prefs.notifications[notificationResourceType].sms.time_slot = [8, 20];
          setValueSMS([8, 20]);
        } else {
          prefs.notifications[notificationResourceType].sms.time_slot = [];
          setValueSMS([]);
        }
      } else if (event.target.name === "on_shift_phone") {
        prefs.notifications[notificationResourceType].phone = {};
        prefs.notifications[notificationResourceType].phone.on_shift =
          event.target.checked;
      } else if (event.target.name === "time_slot_phone") {
        prefs.notifications[notificationResourceType].phone = {};
        if (event.target.checked) {
          prefs.notifications[notificationResourceType].phone.time_slot = [
            8, 20,
          ];
          setValuePhone([8, 20]);
        } else {
          prefs.notifications[notificationResourceType].phone.time_slot = [];
          setValuePhone([]);
        }
      } else if (event.target.name === "on_shift_whatsapp") {
        prefs.notifications[notificationResourceType].whatsapp = {};
        prefs.notifications[notificationResourceType].whatsapp.on_shift =
          event.target.checked;
      } else if (event.target.name === "time_slot_whatsapp") {
        prefs.notifications[notificationResourceType].whatsapp = {};
        if (event.target.checked) {
          prefs.notifications[notificationResourceType].whatsapp.time_slot = [
            8, 20,
          ];
          setValueWhatsapp([8, 20]);
        } else {
          prefs.notifications[notificationResourceType].whatsapp.time_slot = [];
          setValueWhatsapp([]);
        }
      } else {
        prefs.notifications[notificationResourceType][event.target.name] = {
          active: event.target.checked,
        };
      }

      dispatch(profileActions.updateUserPreferences(prefs));
    }
  };

  const onChangeInverted = (type) => {
    if (
      notificationResourceType === "gcn_events" ||
      notificationResourceType === "sources" ||
      notificationResourceType === "favorite_sources" ||
      notificationResourceType === "facility_transactions" ||
      notificationResourceType === "mention" ||
      notificationResourceType === "analysis_services" ||
      notificationResourceType === "observation_plans"
    ) {
      if (type === "sms") {
        const prefs = {
          notifications: {
            [notificationResourceType]: {
              sms: {
                time_slot: valueSMS,
              },
            },
          },
        };
        setValueSMS(valueSMS.reverse());
        setInvertedSMS(!invertedSMS);
        dispatch(profileActions.updateUserPreferences(prefs));
      } else if (type === "phone") {
        const prefs = {
          notifications: {
            [notificationResourceType]: {
              phone: {
                time_slot: valuePhone,
              },
            },
          },
        };
        setValuePhone(valuePhone.reverse());
        setInvertedPhone(!invertedPhone);
        dispatch(profileActions.updateUserPreferences(prefs));
      } else if (type === "whatsapp") {
        const prefs = {
          notifications: {
            [notificationResourceType]: {
              whatsapp: {
                time_slot: valueWhatsapp,
              },
            },
          },
        };
        setValueWhatsapp(valueWhatsapp.reverse());
        setInvertedWhatsapp(!invertedWhatsapp);
        dispatch(profileActions.updateUserPreferences(prefs));
      }
    }
  };

  const handleChecked = (type) => {
    let checked = false;
    checked = profile?.notifications[notificationResourceType][type]?.active;
    return checked;
  };

  const handleSliders = (type, slider_type) => {
    let checked = false;
    if (slider_type === "on_shift") {
      checked =
        profile?.notifications[notificationResourceType][type]?.on_shift;
    } else if (slider_type === "time_slot") {
      checked =
        profile?.notifications[notificationResourceType][type]?.time_slot
          ?.length > 0;
    }
    return checked;
  };

  const valuetext = (val) => `${val}H`;
  const handleChange = (event, newValue) => {
    if (event.target.name === "time_slot_slider_sms") {
      setValueSMS(newValue);
    } else if (event.target.name === "time_slot_slider_phone") {
      setValuePhone(newValue);
    } else if (event.target.name === "time_slot_slider_whatsapp") {
      setValueWhatsapp(newValue);
    }
  };

  const handleChangeCommitted = () => {
    if (
      notificationResourceType === "gcn_events" ||
      notificationResourceType === "sources" ||
      notificationResourceType === "favorite_sources" ||
      notificationResourceType === "facility_transactions" ||
      notificationResourceType === "mention" ||
      notificationResourceType === "analysis_services" ||
      notificationResourceType === "observation_plans"
    ) {
      const prefs = {
        notifications: {
          [notificationResourceType]: {
            sms: {
              [`time_slot`]: valueSMS,
            },
            phone: {
              [`time_slot`]: valuePhone,
            },
            whatsapp: {
              [`time_slot`]: valueWhatsapp,
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
          secondary
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
                          checked={handleSliders("sms", "on_shift")}
                          name="on_shift_sms"
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
                          checked={handleSliders("sms", "time_slot")}
                          name="time_slot_sms"
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
                        value={valueSMS}
                        onChange={handleChange}
                        onChangeCommitted={handleChangeCommitted}
                        valueLabelDisplay="on"
                        getAriaValueText={valuetext}
                        min={0}
                        max={24}
                        step={1}
                        marks
                        track={invertedSMS ? "inverted" : "normal"}
                        name="time_slot_slider_sms"
                      />
                      <Checkbox
                        checked={invertedSMS === true}
                        onChange={() => onChangeInverted("sms")}
                        label="Invert"
                        name="time_slot_slider_sms"
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
              <div className={classes.pref}>
                <FormGroup row className={classes.form_group}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={handleChecked("phone")}
                        name="phone"
                        onChange={prefToggled}
                      />
                    }
                    label=" By Phone Call"
                  />
                  <Tooltip
                    title="Click here to receive notifications by phone call about the selected notification type. You also need to set your phone number in your user profile. Two options will appear, please select at least one."
                    placement="right"
                    classes={{ tooltip: classes.tooltip }}
                  >
                    <HelpOutlineOutlinedIcon />
                  </Tooltip>
                </FormGroup>
              </div>
              {profile?.notifications?.[notificationResourceType]?.phone
                ?.active && (
                <div className={classes.options}>
                  <FormGroup row className={classes.form_group}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={handleSliders("phone", "on_shift")}
                          name="on_shift_phone"
                          onChange={prefToggled}
                        />
                      }
                      label="On Shift"
                    />
                    <Tooltip
                      title="Click here to receive notifications by Phone Call when you are on shift. This is in addition to the time slot option. "
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
                          checked={handleSliders("phone", "time_slot")}
                          name="time_slot_phone"
                          onChange={prefToggled}
                        />
                      }
                      label="Time Slot (UTC)"
                    />
                    <Tooltip
                      title="Click here to receive notifications by Phone Call during a specific time slot. Outside of the time slot, you will not receive any messages on your phone. This is in addition to notifications during shifts, if configured."
                      placement="right"
                      classes={{ tooltip: classes.tooltip }}
                    >
                      <HelpOutlineOutlinedIcon />
                    </Tooltip>
                  </FormGroup>
                  {profile?.notifications?.[notificationResourceType]?.phone
                    ?.time_slot?.length > 0 && (
                    <Box
                      sx={{ width: 300 }}
                      display="flex"
                      flexDirection="row"
                      alignItems="center"
                    >
                      <Slider
                        getAriaLabel={() => "time_slot_slider"}
                        value={valuePhone}
                        onChange={handleChange}
                        onChangeCommitted={handleChangeCommitted}
                        valueLabelDisplay="on"
                        getAriaValueText={valuetext}
                        min={0}
                        max={24}
                        step={1}
                        marks
                        track={invertedPhone ? "inverted" : "normal"}
                        name="time_slot_slider_phone"
                      />
                      <Checkbox
                        checked={invertedPhone === true}
                        onChange={() => onChangeInverted("phone")}
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
              <div className={classes.pref}>
                <FormGroup row className={classes.form_group}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={handleChecked("whatsapp")}
                        name="whatsapp"
                        onChange={prefToggled}
                      />
                    }
                    label=" Message on WhatsApp"
                  />
                  <Tooltip
                    title="Click here to receive notifications on WhatsApp about the selected notification type. You also need to set your phone number in your user profile. Two options will appear, please select at least one."
                    placement="right"
                    classes={{ tooltip: classes.tooltip }}
                  >
                    <HelpOutlineOutlinedIcon />
                  </Tooltip>
                </FormGroup>
              </div>
              {profile?.notifications?.[notificationResourceType]?.whatsapp
                ?.active && (
                <div className={classes.options}>
                  <FormGroup row className={classes.form_group}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={handleSliders("whatsapp", "on_shift")}
                          name="on_shift_whatsapp"
                          onChange={prefToggled}
                        />
                      }
                      label="On Shift"
                    />
                    <Tooltip
                      title="Click here to receive notifications on WhatsApp when you are on shift. This is in addition to the time slot option. "
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
                          checked={handleSliders("whatsapp", "time_slot")}
                          name="time_slot_whatsapp"
                          onChange={prefToggled}
                        />
                      }
                      label="Time Slot (UTC)"
                    />
                    <Tooltip
                      title="Click here to receive notifications on WhatsApp during a specific time slot. Outside of the time slot, you will not receive any messages on your phone. This is in addition to notifications during shifts, if configured."
                      placement="right"
                      classes={{ tooltip: classes.tooltip }}
                    >
                      <HelpOutlineOutlinedIcon />
                    </Tooltip>
                  </FormGroup>
                  {profile?.notifications?.[notificationResourceType]?.whatsapp
                    ?.time_slot?.length > 0 && (
                    <Box
                      sx={{ width: 300 }}
                      display="flex"
                      flexDirection="row"
                      alignItems="center"
                    >
                      <Slider
                        getAriaLabel={() => "time_slot_slider"}
                        value={valueWhatsapp}
                        onChange={handleChange}
                        onChangeCommitted={handleChangeCommitted}
                        valueLabelDisplay="on"
                        getAriaValueText={valuetext}
                        min={0}
                        max={24}
                        step={1}
                        marks
                        track={invertedWhatsapp ? "inverted" : "normal"}
                        name="time_slot_slider_whatsapp"
                      />
                      <Checkbox
                        checked={invertedWhatsapp === true}
                        onChange={() => onChangeInverted("whatsapp")}
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
