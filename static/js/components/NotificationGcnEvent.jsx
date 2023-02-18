import React, { useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import { useForm } from "react-hook-form";
import { makeStyles } from "@mui/styles";
import { showNotification } from "baselayer/components/Notifications";

import { TextField } from "@mui/material";
import Button from "./Button";

import GcnNoticeTypesSelect from "./GcnNoticeTypesSelect";
import GcnTagsSelect from "./GcnTagsSelect";
import GcnPropertiesSelect from "./GcnPropertiesSelect";
import LocalizationTagsSelect from "./LocalizationTagsSelect";
import LocalizationPropertiesSelect from "./LocalizationPropertiesSelect";
import * as profileActions from "../ducks/profile";
import DeletableChips from "./DeletableChips";

const useStyles = makeStyles((theme) => ({
  typography: {
    padding: theme.spacing(2),
  },
  pref: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    marginBottom: theme.spacing(2),
  },
  form: {
    display: "flex",
    flexDirection: "row",
    alignItems: "center",
  },
  button: {
    height: "3rem",
    marginRight: theme.spacing(1),
  },
  form_group: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "left",
    alignItems: "center",
    marginRight: theme.spacing(2),
  },
  tooltip: {
    fontSize: "1rem",
    maxWidth: "30rem",
  },
}));

const NotificationGcnEvent = () => {
  const classes = useStyles();
  const profile = useSelector((state) => state.profile.preferences);
  const { notifications } = useSelector((state) => state.profile.preferences);
  const dispatch = useDispatch();
  const {
    handleSubmit,
    reset,
    formState: { errors },
    register,
  } = useForm();

  const [selectedGcnNoticeTypes, setSelectedGcnNoticeTypes] = useState([]);
  const [selectedGcnTags, setSelectedGcnTags] = useState([]);
  const [selectedGcnProperties, setSelectedGcnProperties] = useState([]);
  const [selectedLocalizationTags, setSelectedLocalizationTags] = useState([]);
  const [selectedLocalizationProperties, setSelectedLocalizationProperties] =
    useState([]);

  const onSubmitGcns = (formValues) => {
    const currentGcnPref = notifications || {};
    currentGcnPref.gcn_events[formValues.GcnNotificationName] = {
      gcn_notice_types: selectedGcnNoticeTypes,
      gcn_tags: selectedGcnTags,
      gcn_properties: selectedGcnProperties,
      localization_tags: selectedLocalizationTags,
      localization_properties: selectedLocalizationProperties,
    };
    const prefs = {
      notifications: currentGcnPref,
    };

    dispatch(profileActions.updateUserPreferences(prefs));

    setSelectedGcnNoticeTypes([]);
    setSelectedGcnTags([]);
    setSelectedGcnProperties([]);
    setSelectedLocalizationTags([]);
    setSelectedLocalizationProperties([]);
    reset({ GcnNotificationName: "" });

    dispatch(showNotification("Gcn notice types updated"));
  };

  const onDelete = (buttonName) => {
    const currentGcnPref = notifications;
    delete currentGcnPref.gcn_events[buttonName];
    const prefs = {
      notifications: currentGcnPref.gcn_events,
    };
    console.log(prefs);
    dispatch(profileActions.updateUserPreferences(prefs));
    dispatch(showNotification("Gcn notice types deleted"));
  };

  return (
    <div className={classes.pref}>
      {profile?.notifications?.gcn_events?.active === true && (
        <>
          {profile && (
            <DeletableChips
              items={Object.keys(profile.notifications.gcn_events)}
              onDelete={onDelete}
              title="Gcn notification "
            />
          )}
          <form onSubmit={handleSubmit(onSubmitGcns)}>
            <div className={classes.form}>
              <TextField
                label="Name"
                {...register("GcnNotificationName", {
                  required: true,
                  validate: (value) => {
                    if (notifications) {
                      return !(value in notifications.gcn_events);
                    }
                    return null;
                  },
                })}
                name="GcnNotificationName"
                id="GcnNotificationNameInput"
                error={!!errors.GcnNotificationName}
                helperText={
                  errors.GcnNotificationName
                    ? "Required/Button with that name already exists"
                    : ""
                }
              />

              <GcnNoticeTypesSelect
                selectedGcnNoticeTypes={selectedGcnNoticeTypes}
                setSelectedGcnNoticeTypes={setSelectedGcnNoticeTypes}
              />
              <GcnTagsSelect
                selectedGcnTags={selectedGcnTags}
                setSelectedGcnTags={setSelectedGcnTags}
              />
              <GcnPropertiesSelect
                selectedGcnProperties={selectedGcnProperties}
                setSelectedGcnProperties={setSelectedGcnProperties}
              />
              <LocalizationTagsSelect
                selectedLocalizationTags={selectedLocalizationTags}
                setSelectedLocalizationTags={setSelectedLocalizationTags}
              />
              <LocalizationPropertiesSelect
                selectedLocalizationProperties={selectedLocalizationProperties}
                setSelectedLocalizationProperties={
                  setSelectedLocalizationProperties
                }
              />
              <Button
                secondary
                type="submit"
                data-testid="addShortcutButton"
                className={classes.button}
              >
                Update
              </Button>
            </div>
          </form>
        </>
      )}
    </div>
  );
};
export default NotificationGcnEvent;
