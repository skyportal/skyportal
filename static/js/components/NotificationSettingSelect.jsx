import React, { useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import FormGroup from "@material-ui/core/FormGroup";
import FormControlLabel from "@material-ui/core/FormControlLabel";
import Switch from "@material-ui/core/Switch";
import { withStyles, makeStyles } from "@material-ui/core/styles";
import PropTypes from "prop-types";
import Dialog from "@material-ui/core/Dialog";
import DialogContent from "@material-ui/core/DialogContent";
import MuiDialogTitle from "@material-ui/core/DialogTitle";
import IconButton from "@material-ui/core/IconButton";
import CloseIcon from "@material-ui/icons/Close";
import Typography from "@material-ui/core/Typography";
import grey from "@material-ui/core/colors/grey";
import { NotificationsActiveOutlined } from "@material-ui/icons";
import { Box, Slider, Checkbox, Button } from "@material-ui/core";
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
          <CloseIcon />
        </IconButton>
      ) : null}
    </MuiDialogTitle>
  )
);

const NotificationSettingSelect = ({ notificationRessourceType }) => {
  const classes = useStyles();
  const [open, setOpen] = useState(false);
  const profile = useSelector((state) => state.profile.preferences);
  const dispatch = useDispatch();
  const [value, setValue] = React.useState([8, 20]);
  const [inverted, setInverted] = React.useState(false);

  const handleClose = () => {
    setOpen(false);
  };

  const prefToggled = (event) => {
    if (
      notificationRessourceType === "gcn_events" ||
      notificationRessourceType === "sources" ||
      notificationRessourceType === "favorite_sources"
    ) {
      const prefs = {
        followed_ressources: {
          [event.target.name]: event.target.checked,
        },
      };

      dispatch(profileActions.updateUserPreferences(prefs));
    }
  };

  const handleChecked = (type) => {
    let checked = false;
    if (notificationRessourceType === "sources" && type === "email") {
      checked = profile.followed_ressources?.sources_by_email === true;
    } else if (notificationRessourceType === "gcn_events" && type === "email") {
      checked = profile.followed_ressources?.gcn_events_by_email === true;
    } else if (
      notificationRessourceType === "favorite_sources" &&
      type === "email"
    ) {
      checked = profile.followed_ressources?.favorite_sources_by_email === true;
    } else if (notificationRessourceType === "sources" && type === "sms") {
      checked = profile.followed_ressources?.sources_by_sms === true;
    } else if (notificationRessourceType === "gcn_events" && type === "sms") {
      checked = profile.followed_ressources?.gcn_events_by_sms === true;
    } else if (
      notificationRessourceType === "favorite_sources" &&
      type === "sms"
    ) {
      checked = profile.followed_ressources?.favorite_sources_by_sms === true;
    } else if (
      notificationRessourceType === "sources" &&
      type === "sms_on_shift"
    ) {
      checked = profile.followed_ressources?.sources_by_sms_on_shift === true;
    } else if (
      notificationRessourceType === "gcn_events" &&
      type === "sms_on_shift"
    ) {
      checked =
        profile.followed_ressources?.gcn_events_by_sms_on_shift === true;
    } else if (
      notificationRessourceType === "favorite_sources" &&
      type === "sms_on_shift"
    ) {
      checked =
        profile.followed_ressources?.favorite_sources_by_sms_on_shift === true;
    }

    return checked;
  };

  const handleLabel = (type) => {
    let label = "";
    if (notificationRessourceType === "sources" && type === "email") {
      label = "Email when a new classification is added to a source";
    } else if (notificationRessourceType === "gcn_events" && type === "email") {
      label =
        "Email when a new GCN event with the selected Notice Type is added";
    } else if (
      notificationRessourceType === "favorite_sources" &&
      type === "email"
    ) {
      label = "Email when something new is done on a favorite source";
    } else if (notificationRessourceType === "sources" && type === "sms") {
      label = "SMS when a new classification is added to a source";
    } else if (notificationRessourceType === "gcn_events" && type === "sms") {
      label = "SMS when a new GCN event with the selected Notice Type is added";
    } else if (
      notificationRessourceType === "favorite_sources" &&
      type === "sms"
    ) {
      label = "SMS when something new is done on a favorite source";
    } else if (
      notificationRessourceType === "sources" &&
      type === "sms_on_shift"
    ) {
      label = "on Shift";
    } else if (
      notificationRessourceType === "gcn_events" &&
      type === "sms_on_shift"
    ) {
      label = "on Shift";
    } else if (
      notificationRessourceType === "favorite_sources" &&
      type === "sms_on_shift"
    ) {
      label = "on Shift";
    }
    return label;
  };

  const handleName = (type) => {
    let name = "";
    if (notificationRessourceType === "sources" && type === "email") {
      name = "sources_by_email";
    } else if (notificationRessourceType === "gcn_events" && type === "email") {
      name = "gcn_events_by_email";
    } else if (
      notificationRessourceType === "favorite_sources" &&
      type === "email"
    ) {
      name = "favorite_sources_by_email";
    } else if (notificationRessourceType === "sources" && type === "sms") {
      name = "sources_by_sms";
    } else if (notificationRessourceType === "gcn_events" && type === "sms") {
      name = "gcn_events_by_sms";
    } else if (
      notificationRessourceType === "favorite_sources" &&
      type === "sms"
    ) {
      name = "favorite_sources_by_sms";
    } else if (
      notificationRessourceType === "sources" &&
      type === "sms_on_shift"
    ) {
      name = "sources_by_sms_on_shift";
    } else if (
      notificationRessourceType === "gcn_events" &&
      type === "sms_on_shift"
    ) {
      name = "gcn_events_by_sms_on_shift";
    } else if (
      notificationRessourceType === "favorite_sources" &&
      type === "sms_on_shift"
    ) {
      name = "favorite_sources_by_sms_on_shift";
    }
    return name;
  };

  const valuetext = (val) => `${val}H`;
  const handleChange = (event, newValue) => {
    setValue(newValue);
  };

  const handleChangeCommitted = () => {
    if (
      notificationRessourceType === "gcn_events" ||
      notificationRessourceType === "sources"
    ) {
      const prefs = {
        followed_ressources: {
          [`${notificationRessourceType}_by_sms_time_slot`]: value,
        },
      };

      dispatch(profileActions.updateUserPreferences(prefs));
    }
  };

  return (
    <div>
      <Button
        variant="contained"
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
                        name={handleName("email")}
                        onChange={prefToggled}
                      />
                    }
                    label={handleLabel("email")}
                  />
                </FormGroup>
              </div>
              <div className={classes.pref}>
                <FormGroup row>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={handleChecked("sms")}
                        name={handleName("sms")}
                        onChange={prefToggled}
                      />
                    }
                    label={handleLabel("sms")}
                  />
                </FormGroup>
              </div>
              <div className={classes.options}>
                {profile?.followed_ressources?.[
                  `${notificationRessourceType}_by_sms`
                ] && (
                  <>
                    <FormGroup row>
                      <FormControlLabel
                        control={
                          <Switch
                            checked={handleChecked("sms_on_shift")}
                            name={handleName("sms_on_shift")}
                            onChange={prefToggled}
                          />
                        }
                        label={handleLabel("sms_on_shift")}
                      />
                    </FormGroup>
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
                        onChange={() => setInverted(!inverted)}
                        label="Invert"
                      />
                    </Box>
                  </>
                )}
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
};

NotificationSettingSelect.propTypes = {
  notificationRessourceType: PropTypes.string,
};

NotificationSettingSelect.defaultProps = {
  notificationRessourceType: "",
};

export default NotificationSettingSelect;
