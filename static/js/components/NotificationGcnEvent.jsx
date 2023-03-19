import React, { useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import { useForm } from "react-hook-form";
import { makeStyles } from "@mui/styles";
import { showNotification } from "baselayer/components/Notifications";

import { TextField, Typography } from "@mui/material";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Button from "./Button";

import GcnNoticeTypesSelect from "./GcnNoticeTypesSelect";
import GcnTagsSelect from "./GcnTagsSelect";
import GcnPropertiesSelect from "./GcnPropertiesSelect";
import LocalizationTagsSelect from "./LocalizationTagsSelect";
import LocalizationPropertiesSelect from "./LocalizationPropertiesSelect";
import * as profileActions from "../ducks/profile";

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

  const [selectedNotification, setSelectedNotification] = useState(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  // Convert the existing notifications to a list format, so that they can be easily modified
  if (!notifications?.gcn_events?.properties) {
    const default_properties = {};
    if (
      notifications?.gcn_events?.gcn_notice_types ||
      notifications?.gcn_events?.gcn_tags ||
      notifications?.gcn_events?.gcn_properties ||
      notifications?.gcn_events?.localization_tags ||
      notifications?.gcn_events?.localization_properties
    ) {
      default_properties.original = {
        gcn_notice_types: notifications?.gcn_events?.gcn_notice_types,
        gcn_tags: notifications?.gcn_events?.gcn_tags,
        gcn_properties: notifications?.gcn_events?.gcn_properties,
        localization_tags: notifications?.gcn_events?.localization_tags,
        localization_properties:
          notifications?.gcn_events?.localization_properties,
      };
    }

    const prefs = {
      notifications: {
        gcn_events: {
          active: true,
          properties: default_properties,
        },
      },
    };

    dispatch(profileActions.updateUserPreferences(prefs));
  }

  const openDialog = (key) => {
    setSelectedNotification(key);
    setDialogOpen(true);
  };

  const closeDialog = () => {
    setDialogOpen(false);
  };

  const onSubmitGcns = (formValues) => {
    const currentGcnPref = notifications.gcn_events.properties || {};
    currentGcnPref[formValues.GcnNotificationName] = {
      gcn_notice_types: selectedGcnNoticeTypes,
      gcn_tags: selectedGcnTags,
      gcn_properties: selectedGcnProperties,
      localization_tags: selectedLocalizationTags,
      localization_properties: selectedLocalizationProperties,
    };
    const prefs = {
      notifications: {
        gcn_events: {
          properties: currentGcnPref,
        },
      },
    };

    dispatch(profileActions.updateUserPreferences(prefs)).then((response) => {
      if (response.status === "success") {
        dispatch(showNotification("GCN notice preferences migrated"));
      } else {
        dispatch(
          showNotification(
            "Cannot automatically migrate GCN notice preferences",
            "error"
          )
        );
      }
    });

    setSelectedGcnNoticeTypes([]);
    setSelectedGcnTags([]);
    setSelectedGcnProperties([]);
    setSelectedLocalizationTags([]);
    setSelectedLocalizationProperties([]);
    reset({ GcnNotificationName: "" });

    dispatch(showNotification("Gcn notice preferences updated"));
  };

  const onDelete = (selected) => {
    const current = notifications.gcn_events.properties;
    delete current[selected];
    const prefs = {
      notifications: {
        gcn_events: {
          properties: current,
        },
      },
    };
    setSelectedNotification(null);
    closeDialog();
    dispatch(profileActions.updateUserPreferences(prefs)).then((response) => {
      if (response.status === "success") {
        dispatch(showNotification("GCN notice preference deleted"));
      } else {
        dispatch(
          showNotification("Can not delete gcn notice preference", "error")
        );
      }
    });
  };

  return (
    <div className={classes.pref}>
      {profile?.notifications?.gcn_events?.active === true && (
        <>
          <form onSubmit={handleSubmit(onSubmitGcns)}>
            <div className={classes.form}>
              <TextField
                style={{ marginBottom: "1rem" }}
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
      <div className={classes.chip}>
        <Typography> Gcn notification </Typography>

        {profile?.notifications?.gcn_events?.properties &&
          Object.keys(profile?.notifications?.gcn_events?.properties)
            .filter((key) => key !== "active")
            .map((key) => (
              <Button
                key={key}
                secondary
                size="small"
                onClick={() => openDialog(key)}
              >
                {`${key}`}
              </Button>
            ))}
        <Dialog
          open={dialogOpen}
          onClose={closeDialog}
          style={{ position: "fixed" }}
        >
          <DialogTitle>{selectedNotification}</DialogTitle>
          <DialogContent>
            <div>
              {selectedNotification && (
                <div>
                  <p>
                    Notice Types:{" "}
                    {
                      profile.notifications.gcn_events?.properties[
                        selectedNotification
                      ]?.gcn_notice_types
                    }
                  </p>
                  <p>
                    Tags:{" "}
                    {
                      profile.notifications.gcn_events?.properties[
                        selectedNotification
                      ]?.gcn_tags
                    }
                  </p>
                  <p>
                    Properties:{" "}
                    {
                      profile.notifications.gcn_events?.properties[
                        selectedNotification
                      ]?.gcn_properties
                    }
                  </p>
                  <p>
                    Localization Tags:{" "}
                    {
                      profile.notifications.gcn_events?.properties[
                        selectedNotification
                      ]?.localization_tags
                    }
                  </p>
                  <p>
                    Localization Properties:{" "}
                    {
                      profile.notifications.gcn_events?.properties[
                        selectedNotification
                      ]?.localization_properties
                    }
                  </p>
                </div>
              )}
              <Button secondary onClick={() => onDelete(selectedNotification)}>
                Delete
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
};
export default NotificationGcnEvent;
