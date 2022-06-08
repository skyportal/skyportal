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

const NotificationPreferences = () => {
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
        title="Notifications Preferences"
        popupText="Enable these to receive notifications on: all sources, favorite sources, gcn events. For each of them, click on the bell to configure the notification settings: by email, sms and/or slack"
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
      <div className={classes.pref}>
        <FormGroup row>
          <FormControlLabel
            control={
              <Switch
                checked={profile.followed_ressources?.favorite_sources === true}
                name="favorite_sources"
                onChange={prefToggled}
              />
            }
            label="Favorite Sources"
          />
        </FormGroup>
        {profile.followed_ressources?.favorite_sources === true && (
          <>
            <div className={classes.pref}>
              <FormGroup row>
                <FormControlLabel
                  control={
                    <Switch
                      checked={
                        profile.followed_ressources
                          ?.favorite_sources_new_comments === true
                      }
                      name="favorite_sources_new_comments"
                      onChange={prefToggled}
                    />
                  }
                  label="New Comments"
                />
                <FormControlLabel
                  control={
                    <Switch
                      checked={
                        profile.followed_ressources
                          ?.favorite_sources_new_spectra === true
                      }
                      name="favorite_sources_new_spectra"
                      onChange={prefToggled}
                    />
                  }
                  label="New Spectra"
                />
                <FormControlLabel
                  control={
                    <Switch
                      checked={
                        profile.followed_ressources
                          ?.favorite_sources_new_classifications === true
                      }
                      name="favorite_sources_new_classifications"
                      onChange={prefToggled}
                    />
                  }
                  label="New Classifications"
                />
              </FormGroup>
            </div>
            <NotificationTypeSelect notificationRessourceType="favorite_sources" />
          </>
        )}
      </div>
    </div>
  );
};

export default NotificationPreferences;
