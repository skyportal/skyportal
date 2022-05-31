import React, { useEffect, useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import { useForm } from "react-hook-form";
import FormGroup from "@material-ui/core/FormGroup";
import FormControlLabel from "@material-ui/core/FormControlLabel";
import Switch from "@material-ui/core/Switch";
import { makeStyles } from "@material-ui/core/styles";
import { Button } from "@material-ui/core";
import * as profileActions from "../ducks/profile";
import UserPreferencesHeader from "./UserPreferencesHeader";
import ClassificationSelect from "./ClassificationSelect";

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
    profile?.followed_ressources?.source_classifications || []
  );

  useEffect(() => {
    setSelectedClassifications(
      profile?.followed_ressources?.source_classifications || []
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

  const onSubmit = () => {
    const prefs = {
      followed_ressources: {
        source_classifications: [...new Set(selectedClassifications)],
      },
    };
    dispatch(profileActions.updateUserPreferences(prefs));
    setSelectedClassifications([...new Set(selectedClassifications)]);
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
                checked={profile.followed_ressources?.source === true}
                name="source"
                onChange={prefToggled}
              />
            }
            label="Source"
          />
        </FormGroup>
        {profile.followed_ressources?.source === true && (
          <form onSubmit={handleSubmit(onSubmit)}>
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
        )}
      </div>
    </div>
  );
};

export default RessourceTypeNotificationsPreferences;
