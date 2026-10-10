import { ReactNode, useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { makeStyles } from "tss-react/mui";
import { showNotification } from "baselayer/components/Notifications";

import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import { useAppDispatch } from "../../../types/hooks";
import Button from "../../Button";

import GcnNoticeTypesSelect from "../../gcn/GcnNoticeTypesSelect";
import GcnTagsSelect from "../../gcn/GcnTagsSelect";
import GcnPropertiesSelect from "../../gcn/GcnPropertiesSelect";
import LocalizationTagsSelect from "../../localization/LocalizationTagsSelect";
import LocalizationPropertiesSelect from "../../localization/LocalizationPropertiesSelect";
import {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
} from "../../../ducks/profile";

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
  formSubGroupDivider: {
    width: "100%",
    height: "2px",
    background: theme.palette.grey[300],
    margin: "0.5rem 0",
  },
}));

const ProfileSection = ({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) => (
  <Box
    sx={{
      display: "flex",
      flexDirection: "column",
      gap: 1.5,
      paddingTop: 2,
      borderTop: 1,
      borderColor: "divider",
    }}
  >
    <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
      {title}
    </Typography>
    {children}
  </Box>
);

const NotificationGcnEvent = () => {
  const { classes } = useStyles();
  const { data: profileData } = useGetProfileQuery();
  const profile = (profileData?.preferences ?? {}) as any;
  const { notifications } = profile;
  const dispatch = useAppDispatch();
  const [updateUserPreferences] = useUpdateUserPreferencesMutation();
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

  // Convert the existing notifications to a list format, so that they can be
  // easily modified. This runs as an effect (not in the render body) so the
  // mutation doesn't dispatch on every render — which caused an infinite
  // PATCH/render loop ("Cannot update a component while rendering").
  useEffect(() => {
    if (!notifications?.gcn_events?.properties) {
      const default_properties: Record<string, any> = {};
      if (
        notifications?.gcn_events?.gcn_notice_types ||
        notifications?.gcn_events?.gcn_tags ||
        notifications?.gcn_events?.gcn_properties ||
        notifications?.gcn_events?.localization_tags ||
        notifications?.gcn_events?.localization_properties
      ) {
        default_properties["original"] = {
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

      updateUserPreferences(prefs);
    }
  }, [notifications, updateUserPreferences]);

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

    updateUserPreferences(prefs)
      .unwrap()
      .then(() => {
        dispatch(showNotification("GCN notice preferences migrated"));
      })
      .catch(() => {
        dispatch(
          showNotification(
            "Cannot automatically migrate GCN notice preferences",
            "error",
          ),
        );
      });

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
    updateUserPreferences(prefs)
      .unwrap()
      .then(() => {
        dispatch(showNotification("GCN notice preference deleted"));
      })
      .catch(() => {
        dispatch(
          showNotification("Can not delete gcn notice preference", "error"),
        );
      });
  };

  const profileNames = Object.keys(
    notifications?.gcn_events?.properties ?? {},
  ).filter((key) => key !== "active");

  return (
    <Box
      sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 1 }}
    >
      <Typography
        variant="caption"
        color="text.secondary"
        sx={{ marginRight: 0.5 }}
      >
        Your profiles
      </Typography>
      {profileNames.map((key) => (
        <Chip
          key={key}
          label={key}
          color="primary"
          variant="outlined"
          onClick={() => openManageProfile(key)}
        />
      ))}
      <Chip
        id="new-gcn-notification-profile"
        label="New profile"
        variant="outlined"
        onClick={openNewProfile}
        sx={{ borderStyle: "dashed" }}
      />
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

      <Dialog
        open={newProfileOpen}
        onClose={closeNewProfile}
        fullWidth
        maxWidth="md"
        slotProps={{
          paper: { component: "form", onSubmit: handleSubmit(onSubmitGcns) },
        }}
      >
        <DialogTitle sx={{ paddingBottom: 0.5 }}>
          New GCN notification profile
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary">
            An event matches this profile when it passes every filter you set.
            Empty filters are ignored.
          </Typography>
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              gap: 2.5,
              paddingTop: 2.5,
            }}
          >
            <TextField
              fullWidth
              label="Name"
              {...register("GcnNotificationName", {
                required: true,
                validate: (value) =>
                  !(value in (notifications?.gcn_events?.properties ?? {})),
              })}
              name="GcnNotificationName"
              id="GcnNotificationNameInput"
              error={!!errors["GcnNotificationName"]}
              helperText={
                errors["GcnNotificationName"]
                  ? "Pick a name that no other profile uses"
                  : ""
              }
            />
            <ProfileSection title="Event">
              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" },
                  gap: 1.5,
                }}
              >
                <GcnNoticeTypesSelect
                  selectedGcnNoticeTypes={selectedGcnNoticeTypes}
                  setSelectedGcnNoticeTypes={setSelectedGcnNoticeTypes}
                />
                <GcnTagsSelect
                  selectedGcnTags={selectedGcnTags}
                  setSelectedGcnTags={setSelectedGcnTags}
                />
              </Box>
              <GcnPropertiesSelect
                selectedGcnProperties={selectedGcnProperties}
                setSelectedGcnProperties={setSelectedGcnProperties}
                conversions={conversions}
                comparators={comparators}
              />
            </ProfileSection>
            <ProfileSection title="Localization">
              <LocalizationTagsSelect
                selectedLocalizationTags={selectedLocalizationTags}
                setSelectedLocalizationTags={setSelectedLocalizationTags}
              />
              <LocalizationPropertiesSelect
                selectedLocalizationProperties={selectedLocalizationProperties}
                setSelectedLocalizationProperties={
                  setSelectedLocalizationProperties
                }
                comparators={comparators}
              />
            </ProfileSection>
          </Box>
        </DialogContent>
        <DialogActions sx={{ padding: "0.75rem 1.5rem 1.25rem" }}>
          <Button secondary onClick={closeNewProfile}>
            Cancel
          </Button>
          <Button primary type="submit" data-testid="addShortcutButton">
            Create
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};
export default NotificationGcnEvent;
