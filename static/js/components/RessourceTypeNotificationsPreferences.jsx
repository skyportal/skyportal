import React, { useEffect, useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import { useForm } from "react-hook-form";
import FormGroup from "@material-ui/core/FormGroup";
import FormControlLabel from "@material-ui/core/FormControlLabel";
import Switch from "@material-ui/core/Switch";
import { makeStyles } from "@material-ui/core/styles";
import { Button } from "@material-ui/core";
import { showNotification } from "baselayer/components/Notifications";
import UserPreferencesHeader from "./UserPreferencesHeader";
import ClassificationSelect from "./ClassificationSelect";
import GcnNoticeTypesSelect from "./GcnNoticeTypesSelect";
import NotificationTypeSelect from "./NotificationSettingSelect";
import * as profileActions from "../ducks/profile";

const useStyles = makeStyles((theme) => ({
  typography: {
    padding: theme.spacing(2),
  },
  pref: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    width: "30rem",
    height: "5rem",
  },
  form: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    width: "20rem",
  },
  button: {
    height: "3rem",
  },
}));

const RessourceTypeNotificationsPreferences = () => {
  const classes = useStyles();
  const profile = useSelector((state) => state.profile.preferences);
  const dispatch = useDispatch();
  const { handleSubmit } = useForm();
  const [selectedClassifications, setSelectedClassifications] = useState(
    profile?.followed_ressources?.sources_classifications || []
  );

  const [selectedGcnNoticeTypes, setSelectedGcnNoticeTypes] = useState(
    profile?.followed_ressources?.gcn_notice_types || []
  );

  useEffect(() => {
    setSelectedClassifications(
      profile?.followed_ressources?.sources_classifications || []
    );
    setSelectedGcnNoticeTypes(
      profile?.followed_ressources?.gcn_notice_types || []
    );
  }, [profile]);

  const prefToggled = (event) => {
    const prefs = {
      followed_ressources: {
        [event.target.name]: event.target.checked,
      },
    };

    dispatch(profileActions.updateUserPreferences(prefs));
  };

  const onSubmitSources = () => {
    const prefs = {
      followed_ressources: {
        sources_classifications: [...new Set(selectedClassifications)],
      },
    };
    dispatch(profileActions.updateUserPreferences(prefs));
    setSelectedClassifications([...new Set(selectedClassifications)]);
    dispatch(showNotification("Sources classifications updated"));
  };

  const onSubmitGcns = () => {
    const prefs = {
      followed_ressources: {
        gcn_notice_types: [...new Set(selectedGcnNoticeTypes)],
      },
    };
    dispatch(profileActions.updateUserPreferences(prefs));
    setSelectedGcnNoticeTypes([...new Set(selectedGcnNoticeTypes)]);
    dispatch(showNotification("Gcn notice types updated"));
  };

  return (
    <div>
      <UserPreferencesHeader
        title="Notifications For Ressource Type Activity"
        popupText="Enable these to receive notifications for all elements of a ressource type, given certain conditions (ex: Notify me for all sources, that get classified as SN or KN)."
      />
      <div className={classes.pref}>
        <FormGroup row>
          <FormControlLabel
            control={
              <Switch
                checked={profile.followed_ressources?.sources === true}
                name="sources"
                onChange={prefToggled}
              />
            }
            label="All Sources"
          />
        </FormGroup>
        {profile.followed_ressources?.sources === true && (
          <>
            <form onSubmit={handleSubmit(onSubmitSources)}>
              <div className={classes.form}>
                <ClassificationSelect
                  selectedClassifications={selectedClassifications}
                  setSelectedClassifications={setSelectedClassifications}
                />
                <Button
                  variant="contained"
                  type="submit"
                  data-testid="addShortcutButton"
                  className={classes.button}
                >
                  Update
                </Button>
              </div>
            </form>
            <NotificationTypeSelect notificationRessourceType="sources" />
          </>
        )}
      </div>
      <div className={classes.pref}>
        <FormGroup row>
          <FormControlLabel
            control={
              <Switch
                checked={profile.followed_ressources?.gcn_events === true}
                name="gcn_events"
                onChange={prefToggled}
              />
            }
            label="All GCN Events"
          />
        </FormGroup>
        {profile.followed_ressources?.gcn_events === true && (
          <>
            <form onSubmit={handleSubmit(onSubmitGcns)}>
              <div className={classes.form}>
                <GcnNoticeTypesSelect
                  selectedGcnNoticeTypes={selectedGcnNoticeTypes}
                  setSelectedGcnNoticeTypes={setSelectedGcnNoticeTypes}
                />
                <Button
                  variant="contained"
                  type="submit"
                  data-testid="addShortcutButton"
                  className={classes.button}
                >
                  Update
                </Button>
              </div>
            </form>
            <NotificationTypeSelect notificationRessourceType="gcn_events" />
          </>
        )}
      </div>
    </div>
  );
};

export default RessourceTypeNotificationsPreferences;
