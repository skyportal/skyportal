import React, { useState } from "react";
import { useForm } from "react-hook-form";
import { makeStyles } from "tss-react/mui";
import { showNotification } from "baselayer/components/Notifications";

import Chip from "@mui/material/Chip";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import { useAppDispatch, useAppSelector } from "../../../types/hooks";
import Button from "../../Button";

import GcnNoticeTypesSelect from "../../gcn/GcnNoticeTypesSelect";
import GcnTagsSelect from "../../gcn/GcnTagsSelect";
import GcnPropertiesSelect from "../../gcn/GcnPropertiesSelect";
import LocalizationTagsSelect from "../../localization/LocalizationTagsSelect";
import LocalizationPropertiesSelect from "../../localization/LocalizationPropertiesSelect";
import * as profileActions from "../../../ducks/profile";

const conversions: Record<string, any> = {
  FAR: {
    backendUnit: "Hz",
    frontendUnit: "Per year",
    BackendToFrontend: (val: any) => parseFloat(val) * (365.25 * 24 * 60 * 60),
    FrontendToBackend: (val: any) => parseFloat(val) / (365.25 * 24 * 60 * 60),
  },
};

const comparators: Record<string, string> = {
  lt: "<",
  le: "<=",
  eq: "=",
  ne: "!=",
  ge: ">",
  gt: ">=",
};

const useStyles = makeStyles()((theme) => ({
  pref: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
  },
  form: {
    display: "flex",
    flexDirection: "column",
    justifyContent: "center",
    alignItems: "left",
  },
  button: {
    marginLeft: theme.spacing(2),
  },
  form_group: {
    display: "flex",
    flexDirection: "column",
    alignItems: "left",
    gap: "0.5rem",
    width: "100%",
    marginTop: "0.5rem",
    marginBottom: "0.5rem",
  },
  form_group_title: {
    fontSize: "1.2rem",
  },
  form_subgroup: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "left",
    alignItems: "center",
    gap: "0.25rem",
    width: "100%",
    "& > div": {
      width: "100%",
    },
  },
  chips: {
    padding: "0",
    margin: "0",
    "& > *": {
      marginTop: 0,
      marginBottom: 0,
      marginLeft: "0.05rem",
      marginRight: "0.05rem",
      fontSize: "1rem",
    },
  },
  formGroupDivider: {
    width: "100%",
    height: "2px",
    background: theme.palette.grey[600],
    margin: "0.5rem 0",
  },
  formSubGroupDivider: {
    width: "100%",
    height: "2px",
    background: theme.palette.grey[300],
    margin: "0.5rem 0",
  },
}));

const NotificationGcnEvent = () => {
  const { classes } = useStyles();
  const profile = useAppSelector((state) => state.profile.preferences) as any;
  const { notifications } = useAppSelector(
    (state) => state.profile.preferences,
  ) as any;
  const dispatch = useAppDispatch();
  const {
    handleSubmit,
    reset,
    formState: { errors },
    register,
  } = useForm();

  const [selectedGcnNoticeTypes, setSelectedGcnNoticeTypes] = useState<any[]>(
    [],
  );
  const [selectedGcnTags, setSelectedGcnTags] = useState<any[]>([]);
  const [selectedGcnProperties, setSelectedGcnProperties] = useState<any[]>([]);
  const [selectedLocalizationTags, setSelectedLocalizationTags] = useState<
    any[]
  >([]);
  const [selectedLocalizationProperties, setSelectedLocalizationProperties] =
    useState<any[]>([]);

  const [selectedNotification, setSelectedNotification] = useState<any>(null);
  const [manageProfileOpen, setManageProfileOpen] = useState(false);
  const [newProfileOpen, setNewProfileOpen] = useState(false);

  // Convert the existing notifications to a list format, so that they can be easily modified
  if (!notifications?.gcn_events?.properties) {
    const default_properties: Record<string, any> = {};
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

  const openManageProfile = (key: any) => {
    setSelectedNotification(key);
    setManageProfileOpen(true);
  };

  const closeManageProfile = () => {
    setManageProfileOpen(false);
  };

  const openNewProfile = () => {
    setNewProfileOpen(true);
  };

  const closeNewProfile = () => {
    setNewProfileOpen(false);
  };

  const onSubmitGcns = (formValues: any) => {
    const prefs = {
      notifications: {
        gcn_events: {
          properties: {
            ...(notifications.gcn_events.properties || {}),
            [formValues.GcnNotificationName]: {
              gcn_notice_types: selectedGcnNoticeTypes,
              gcn_tags: selectedGcnTags,
              gcn_properties: selectedGcnProperties,
              localization_tags: selectedLocalizationTags,
              localization_properties: selectedLocalizationProperties,
            },
          },
        },
      },
    };

    dispatch(profileActions.updateUserPreferences(prefs)).then(
      (response: any) => {
        if (response.status === "success") {
          dispatch(showNotification("GCN notice preferences migrated"));
        } else {
          dispatch(
            showNotification(
              "Cannot automatically migrate GCN notice preferences",
              "error",
            ),
          );
        }
      },
    );

    setSelectedGcnNoticeTypes([]);
    setSelectedGcnTags([]);
    setSelectedGcnProperties([]);
    setSelectedLocalizationTags([]);
    setSelectedLocalizationProperties([]);
    reset({ GcnNotificationName: "" });

    closeNewProfile();

    dispatch(showNotification("Gcn notice preferences updated"));
  };

  const onDelete = (selected: any) => {
    const prefs = {
      notifications: {
        gcn_events: {
          properties: Object.fromEntries(
            Object.entries(notifications.gcn_events.properties).filter(
              ([key]) => key !== selected,
            ),
          ),
        },
      },
    };
    setSelectedNotification(null);
    closeManageProfile();
    dispatch(profileActions.updateUserPreferences(prefs)).then(
      (response: any) => {
        if (response.status === "success") {
          dispatch(showNotification("GCN notice preference deleted"));
        } else {
          dispatch(
            showNotification("Can not delete gcn notice preference", "error"),
          );
        }
      },
    );
  };

  return (
    <div className={classes.pref}>
      <div className={classes.chips}>
        {profile?.notifications?.gcn_events?.properties &&
          Object.keys(profile?.notifications?.gcn_events?.properties)
            .filter((key) => key !== "active")
            .map((key) => (
              <Chip
                label={`${key}`}
                key={key}
                size="small"
                onClick={() => openManageProfile(key)}
                {...({ secondary: true } as any)}
              />
            ))}
        <Dialog
          open={manageProfileOpen}
          onClose={closeManageProfile}
          maxWidth="lg"
        >
          <DialogTitle style={{ fontSize: "1.4rem" }}>
            {selectedNotification}
          </DialogTitle>
          <DialogContent>
            <div>
              {selectedNotification && (
                <div>
                  <p>
                    Notice Types:{" "}
                    {(
                      profile.notifications.gcn_events?.properties[
                        selectedNotification
                      ]?.gcn_notice_types || []
                    ).join(", ")}
                  </p>
                  <div className={classes.formSubGroupDivider} />
                  <p>
                    Tags:{" "}
                    {(
                      profile.notifications.gcn_events?.properties[
                        selectedNotification
                      ]?.gcn_tags || []
                    ).join(", ")}
                  </p>
                  <div className={classes.formSubGroupDivider} />
                  <p>
                    Properties:{" "}
                    <ul>
                      {(
                        profile.notifications.gcn_events?.properties[
                          selectedNotification
                        ]?.gcn_properties || []
                      ).map((prop: any) => (
                        <li
                          key={prop}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            flexDirection: "row",
                            gap: "0.5rem",
                          }}
                        >
                          <p>{prop.split(":")[0].trim()}</p>
                          <p>{comparators[prop.split(":")[2].trim()]}</p>
                          <p>
                            {conversions[prop.split(":")[0].trim()]
                              ? conversions[
                                  prop.split(":")[0].trim()
                                ].BackendToFrontend(prop.split(":")[1].trim())
                              : prop.split(":")[1].trim()}
                          </p>
                          <p>
                            {conversions[prop.split(":")[0].trim()]
                              ?.frontendUnit || ""}{" "}
                          </p>
                        </li>
                      ))}
                    </ul>
                  </p>
                  <div className={classes.formSubGroupDivider} />
                  <p>
                    Localization Tags:{" "}
                    {(
                      profile.notifications.gcn_events?.properties[
                        selectedNotification
                      ]?.localization_tags || []
                    ).join(", ")}
                  </p>
                  <div className={classes.formSubGroupDivider} />
                  <p>
                    Localization Properties:{" "}
                    <ul>
                      {(
                        profile.notifications.gcn_events?.properties[
                          selectedNotification
                        ]?.localization_properties || []
                      ).map((prop: any) => (
                        <li
                          key={prop}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            flexDirection: "row",
                            gap: "0.5rem",
                          }}
                        >
                          <p>{prop.split(":")[0].trim()}</p>
                          <p>{comparators[prop.split(":")[2].trim()]}</p>
                          <p>
                            {conversions[prop.split(":")[0].trim()]
                              ? conversions[
                                  prop.split(":")[0].trim()
                                ].BackendToFrontend(prop.split(":")[1].trim())
                              : prop.split(":")[1].trim()}
                          </p>
                          <p>
                            {conversions[prop.split(":")[0].trim()]
                              ?.frontendUnit || ""}{" "}
                          </p>
                        </li>
                      ))}
                    </ul>
                  </p>
                </div>
              )}
              <Button secondary onClick={() => onDelete(selectedNotification)}>
                Delete
              </Button>
            </div>
          </DialogContent>
        </Dialog>

        <Dialog open={newProfileOpen} onClose={closeNewProfile} maxWidth="lg">
          <DialogTitle>New GCN Notification Profile</DialogTitle>
          <DialogContent>
            <form onSubmit={handleSubmit(onSubmitGcns)}>
              <div className={classes.form}>
                <div className={classes.form_group}>
                  <TextField
                    style={{ width: "100%" }}
                    label="Name"
                    {...register("GcnNotificationName", {
                      required: true,
                      validate: (value) => {
                        if (notifications) {
                          return !(value in notifications.gcn_events);
                        }
                        return true;
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
                </div>
                <div className={classes.formGroupDivider} />
                <div className={classes.form_group}>
                  <Typography className={classes.form_group_title}>
                    Event Filtering
                  </Typography>
                  <div className={classes.form_subgroup}>
                    <GcnNoticeTypesSelect
                      selectedGcnNoticeTypes={selectedGcnNoticeTypes}
                      setSelectedGcnNoticeTypes={setSelectedGcnNoticeTypes}
                    />
                    <GcnTagsSelect
                      selectedGcnTags={selectedGcnTags}
                      setSelectedGcnTags={setSelectedGcnTags}
                    />
                  </div>
                  <div className={classes.formSubGroupDivider} />
                  <div className={classes.form_subgroup}>
                    <GcnPropertiesSelect
                      selectedGcnProperties={selectedGcnProperties}
                      setSelectedGcnProperties={setSelectedGcnProperties}
                      conversions={conversions}
                      comparators={comparators}
                    />
                  </div>
                </div>
                <div className={classes.formGroupDivider} />
                <div className={classes.form_group}>
                  <Typography className={classes.form_group_title}>
                    Localization Filtering
                  </Typography>
                  <div className={classes.form_subgroup}>
                    <LocalizationTagsSelect
                      selectedLocalizationTags={selectedLocalizationTags}
                      setSelectedLocalizationTags={setSelectedLocalizationTags}
                    />
                  </div>
                  <div className={classes.formSubGroupDivider} />
                  <div className={classes.form_subgroup}>
                    <LocalizationPropertiesSelect
                      selectedLocalizationProperties={
                        selectedLocalizationProperties
                      }
                      setSelectedLocalizationProperties={
                        setSelectedLocalizationProperties
                      }
                      comparators={comparators}
                    />
                  </div>
                </div>
                <Button
                  secondary
                  type="submit"
                  data-testid="addShortcutButton"
                  style={{ marginTop: "1rem" }}
                >
                  Create
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>
      {profile?.notifications?.gcn_events?.active === true && (
        <Button
          className={classes.button}
          secondary
          onClick={() => openNewProfile()}
          id="new-gcn-notification-profile"
        >
          Create New Profile
        </Button>
      )}
    </div>
  );
};
export default NotificationGcnEvent;
