import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useForm } from "react-hook-form";
import { makeStyles } from "@mui/styles";
import { showNotification } from "baselayer/components/Notifications";

import FormGroup from "@mui/material/FormGroup";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";
import Tooltip from "@mui/material/Tooltip";
import HelpOutlineOutlinedIcon from "@mui/icons-material/HelpOutlineOutlined";
import Button from "./Button";

import UserPreferencesHeader from "./user/UserPreferencesHeader";
import ClassificationSelect from "./classification/ClassificationSelect";
import NotificationSettingsSelect from "./NotificationSettingsSelect";
import * as profileActions from "../ducks/profile";
import NotificationGcnEvent from "./NotificationGcnEvent";
import { SelectLabelWithChips } from "./SelectWithChips";

const useStyles = makeStyles((theme) => ({
  typography: {
    padding: theme.spacing(2),
  },
  pref: {
    display: "flex",
    flexDirection: "row",
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
    marginLeft: theme.spacing(2),
  },
  form_group: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "left",
    alignItems: "center",
    marginRight: theme.spacing(2),
  },
  form_group_with_spacing: {
    // same as above, but with gaps between the elements
    display: "flex",
    flexDirection: "row",
    justifyContent: "left",
    alignItems: "center",
    "& > *": {
      marginLeft: theme.spacing(1),
    },
  },
  form_column: {
    display: "flex",
    flexDirection: "column",
    justifyContent: "left",
    alignItems: "center",
    marginRight: theme.spacing(2),
  },
  tooltip: {
    fontSize: "1rem",
    maxWidth: "30rem",
  },
}));

const NotificationPreferences = () => {
  const classes = useStyles();
  const profile = useSelector((state) => state.profile.preferences);
  const groups = useSelector((state) => state.groups.userAccessible);
  const { allocationListApiClassname } = useSelector(
    (state) => state.allocations,
  );
  const dispatch = useDispatch();
  const { handleSubmit } = useForm();
  const [selectedClassifications, setSelectedClassifications] = useState(
    profile?.notifications?.sources?.classifications || [],
  );
  const [selectedGroups, setSelectedGroups] = useState([]);
  const [selectedAllocations, setSelectedAllocations] = useState([]);

  let sortedGroups = groups.sort((a, b) => {
    if (a.name.toLowerCase() < b.name.toLowerCase()) {
      return -1;
    }
    if (a.name.toLowerCase() > b.name.toLowerCase()) {
      return 1;
    }
    return 0;
  });
  sortedGroups = sortedGroups.map((group) => ({
    id: group?.id,
    label: group?.name,
  }));

  let sortedAllocations = (allocationListApiClassname || []).map(
    (allocation) => ({
      id: allocation?.id,
      label: `${allocation.instrument?.name} [${allocation?.pi}]`,
    }),
  );

  // then sort the allocations by label
  sortedAllocations = sortedAllocations.sort((a, b) => {
    if (a.label.toLowerCase() < b.label.toLowerCase()) {
      return -1;
    }
    if (a.label.toLowerCase() > b.label.toLowerCase()) {
      return 1;
    }
    return 0;
  });

  const onGroupSelectChange = (event) => {
    let new_selected_groups = [];
    event.target.value.forEach((group) => {
      if (
        !new_selected_groups.some(
          (selected_group) => selected_group?.id === group?.id,
        )
      ) {
        new_selected_groups.push(group);
      } else {
        // remove the user from the list
        new_selected_groups = new_selected_groups.filter(
          (selected_group) => selected_group?.id !== group?.id,
        );
      }
    });
    setSelectedGroups(new_selected_groups);
  };

  const onAllocationSelectChange = (event) => {
    let new_selected_allocations = [];
    event.target.value.forEach((allocation) => {
      if (
        !new_selected_allocations.some(
          (selected_allocation) => selected_allocation?.id === allocation?.id,
        )
      ) {
        new_selected_allocations.push(allocation);
      } else {
        new_selected_allocations = new_selected_allocations.filter(
          (selected_allocation) => selected_allocation?.id !== allocation?.id,
        );
      }
    });
    setSelectedAllocations(new_selected_allocations);
  };

  useEffect(() => {
    if (selectedGroups.length === 0 && groups?.length > 0) {
      setSelectedClassifications(
        profile?.notifications?.sources?.classifications || [],
      );
      let existingGroups =
        profile?.notifications?.sources?.groups?.map((groupId) =>
          groups.find((g) => g.id === groupId),
        ) || [];
      existingGroups = existingGroups.filter((group) => group);
      existingGroups = existingGroups.map((group) => ({
        id: group?.id,
        label: group?.name,
      }));

      setSelectedGroups(existingGroups || []);
    }
  }, [profile, groups]);

  useEffect(() => {
    if (
      selectedAllocations.length === 0 &&
      allocationListApiClassname?.length > 0
    ) {
      let existingAllocations =
        profile?.notifications?.sources?.allocations?.map((allocationId) =>
          allocationListApiClassname.find((a) => a.id === allocationId),
        ) || [];
      existingAllocations = existingAllocations.filter(
        (allocation) => allocation,
      );
      existingAllocations = existingAllocations.map((allocation) => ({
        id: allocation?.id,
        label: `${allocation.instrument?.name} [${allocation?.pi}]`,
      }));

      setSelectedAllocations(existingAllocations || []);
    }
  }, [profile, allocationListApiClassname]);

  const prefToggled = (event) => {
    const prefs = {
      notifications: {},
    };
    if (
      event.target.name === "sources" ||
      event.target.name === "gcn_events" ||
      event.target.name === "mention" ||
      event.target.name === "favorite_sources" ||
      event.target.name === "facility_transactions" ||
      event.target.name === "analysis_services" ||
      event.target.name === "observation_plans"
    ) {
      prefs.notifications[event.target.name] = {
        active: event.target.checked,
      };
    } else if (event.target.name === "gcn_events_new_tags") {
      prefs.notifications.gcn_events = {
        new_tags: event.target.checked,
      };
    } else if (event.target.name === "favorite_sources_new_comments") {
      prefs.notifications.favorite_sources = {
        new_comments: event.target.checked,
      };
    } else if (event.target.name === "favorite_sources_new_classifications") {
      prefs.notifications.favorite_sources = {
        new_classifications: event.target.checked,
      };
    } else if (event.target.name === "favorite_sources_new_spectra") {
      prefs.notifications.favorite_sources = {
        new_spectra: event.target.checked,
      };
    } else if (event.target.name === "favorite_sources_new_bot_comments") {
      prefs.notifications.favorite_sources = {
        new_bot_comments: event.target.checked,
      };
    } else if (
      event.target.name === "favorite_sources_new_ml_classifications"
    ) {
      prefs.notifications.favorite_sources = {
        new_ml_classifications: event.target.checked,
      };
    } else if (event.target.name === "sources_new_spectra") {
      prefs.notifications.sources = {
        new_spectra: event.target.checked,
      };
    }

    dispatch(profileActions.updateUserPreferences(prefs));
  };

  const onSubmitSources = () => {
    const prefs = {
      notifications: {
        sources: {
          classifications: [...new Set(selectedClassifications)],
          groups: [...new Set(selectedGroups.map((group) => group.id))],
          allocations: [
            ...new Set(selectedAllocations.map((allocation) => allocation.id)),
          ],
        },
      },
    };
    dispatch(profileActions.updateUserPreferences(prefs));
    setSelectedClassifications([...new Set(selectedClassifications)]);
    setSelectedGroups([...new Set(selectedGroups)]);
    dispatch(showNotification("Sources classifications updated"));
  };

  return (
    <div>
      <UserPreferencesHeader
        title="Notifications Preferences"
        popupText="Enable these to receive notifications on: all sources, favorite sources, gcn events, facility transactions. For each of them, click on the bell to configure the notification settings: email, sms and/or slack"
      />
      <div className={classes.pref}>
        <FormGroup row className={classes.form_group}>
          <FormControlLabel
            control={
              <Switch
                checked={profile?.notifications?.sources?.active === true}
                name="sources"
                onChange={prefToggled}
              />
            }
            label="Sources"
          />
          <Tooltip
            title="This allows you to be notified for all sources, based on a certain criteria. For now, you can select classification(s) to be notified for, when added to any source."
            placement="right"
            classes={{ tooltip: classes.tooltip }}
          >
            <HelpOutlineOutlinedIcon />
          </Tooltip>
        </FormGroup>
        {profile?.notifications?.sources?.active === true && (
          <FormGroup row className={classes.form_group}>
            <form onSubmit={handleSubmit(onSubmitSources)}>
              <div className={classes.form}>
                <div className={classes.form_group_with_spacing}>
                  <ClassificationSelect
                    selectedClassifications={selectedClassifications}
                    setSelectedClassifications={setSelectedClassifications}
                  />
                  {sortedGroups?.length > 0 && (
                    <SelectLabelWithChips
                      label="Groups (optional)"
                      id="groups-select"
                      initValue={selectedGroups}
                      onChange={onGroupSelectChange}
                      options={sortedGroups}
                    />
                  )}
                  {sortedGroups?.length > 0 && (
                    <SelectLabelWithChips
                      label="Allocations (optional)"
                      id="allocations-select"
                      initValue={selectedAllocations}
                      onChange={onAllocationSelectChange}
                      options={sortedAllocations}
                    />
                  )}
                  <FormControlLabel
                    control={
                      <Switch
                        checked={
                          profile?.notifications?.sources?.new_spectra === true
                        }
                        name="sources_new_spectra"
                        onChange={prefToggled}
                      />
                    }
                    label="New spectrum"
                  />
                </div>
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
            <NotificationSettingsSelect notificationResourceType="sources" />
          </FormGroup>
        )}
      </div>
      <div className={classes.pref}>
        <FormGroup row className={classes.form_group}>
          <FormControlLabel
            control={
              <Switch
                checked={profile?.notifications?.gcn_events?.active === true}
                name="gcn_events"
                onChange={prefToggled}
              />
            }
            label="GCN Events"
          />
          <Tooltip
            title="This allows you to be notified when GCN events receive a new skymap (and optionally when new tags are added to the skymap). You must create at least one notification profile"
            placement="right"
            classes={{ tooltip: classes.tooltip }}
          >
            <HelpOutlineOutlinedIcon />
          </Tooltip>
        </FormGroup>
        {profile?.notifications?.gcn_events?.active === true && (
          <div className={classes.form}>
            <FormGroup row className={classes.form_group}>
              <FormControlLabel
                control={
                  <Switch
                    checked={
                      profile?.notifications?.gcn_events?.new_tags === true
                    }
                    name="gcn_events_new_tags"
                    onChange={prefToggled}
                  />
                }
                label="Notify on new tags"
              />
            </FormGroup>
          </div>
        )}
        {profile?.notifications?.gcn_events?.active === true && (
          <>
            <NotificationGcnEvent />
            <NotificationSettingsSelect notificationResourceType="gcn_events" />
          </>
        )}
      </div>
      <div className={classes.pref}>
        <FormGroup row className={classes.form_group}>
          <FormControlLabel
            control={
              <Switch
                checked={
                  profile?.notifications?.facility_transactions?.active === true
                }
                name="facility_transactions"
                onChange={prefToggled}
              />
            }
            label="Facility Transactions / Follow-up Requests"
          />
          <Tooltip
            title="This allows you to be notified for all facility transactions (followup requests, observation plans)."
            placement="right"
            classes={{ tooltip: classes.tooltip }}
          >
            <HelpOutlineOutlinedIcon />
          </Tooltip>
        </FormGroup>
        {profile?.notifications?.facility_transactions?.active === true && (
          <NotificationSettingsSelect notificationResourceType="facility_transactions" />
        )}
      </div>
      <div className={classes.pref}>
        <FormGroup row className={classes.form_group}>
          <FormControlLabel
            control={
              <Switch
                checked={
                  profile?.notifications?.analysis_services?.active === true
                }
                name="analysis_services"
                onChange={prefToggled}
              />
            }
            label="Analysis Services"
          />
          <Tooltip
            title="This allows you to be notified for all completed analysis services."
            placement="right"
            classes={{ tooltip: classes.tooltip }}
          >
            <HelpOutlineOutlinedIcon />
          </Tooltip>
        </FormGroup>
        {profile?.notifications?.analysis_services?.active === true && (
          <NotificationSettingsSelect notificationResourceType="analysis_services" />
        )}
      </div>
      <div className={classes.pref}>
        <FormGroup row className={classes.form_group}>
          <FormControlLabel
            control={
              <Switch
                checked={
                  profile?.notifications?.favorite_sources?.active === true
                }
                name="favorite_sources"
                onChange={prefToggled}
              />
            }
            label="Favorite Sources"
          />
          <Tooltip
            title="This allows you to be notified when certain actions are performed by users on your favorite sources. You can select to be notified about new comments, new classifications and new spectra added to a favorite source."
            placement="right"
            classes={{ tooltip: classes.tooltip }}
          >
            <HelpOutlineOutlinedIcon />
          </Tooltip>
        </FormGroup>
        {profile?.notifications?.favorite_sources?.active === true && (
          <div className={classes.form}>
            <div className={classes.form_column}>
              <FormGroup row className={classes.form_group}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={
                        profile?.notifications?.favorite_sources
                          ?.new_comments === true
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
                        profile?.notifications?.favorite_sources
                          ?.new_spectra === true
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
                        profile?.notifications?.favorite_sources
                          ?.new_classifications === true
                      }
                      name="favorite_sources_new_classifications"
                      onChange={prefToggled}
                    />
                  }
                  label="New Classifications"
                />
              </FormGroup>
              <FormGroup row className={classes.form_group}>
                {profile?.notifications?.favorite_sources?.new_comments ===
                  true && (
                  <FormControlLabel
                    control={
                      <Switch
                        checked={
                          profile?.notifications?.favorite_sources
                            ?.new_bot_comments === true
                        }
                        name="favorite_sources_new_bot_comments"
                        onChange={prefToggled}
                      />
                    }
                    label="Also on BOT comments?"
                  />
                )}
                {profile?.notifications?.favorite_sources
                  ?.new_classifications === true && (
                  <FormControlLabel
                    control={
                      <Switch
                        checked={
                          profile?.notifications?.favorite_sources
                            ?.new_ml_classifications === true
                        }
                        name="favorite_sources_new_ml_classifications"
                        onChange={prefToggled}
                      />
                    }
                    label="Also on ML classifications?"
                  />
                )}
              </FormGroup>
            </div>
          </div>
        )}
        {profile?.notifications?.favorite_sources?.active === true && (
          <NotificationSettingsSelect notificationResourceType="favorite_sources" />
        )}
      </div>
      <div className={classes.pref}>
        <FormGroup row className={classes.form_group}>
          <FormControlLabel
            control={
              <Switch
                checked={profile?.notifications?.mention?.active === true}
                name="mention"
                onChange={prefToggled}
              />
            }
            label="@ Mentions"
          />
          <Tooltip
            title="On SkyPortal, you will always be notified when a user mentions you. If you activate this, it will simply allow you to specify in the settings if you want to also be notified by email, sms and/or slack."
            placement="right"
            classes={{ tooltip: classes.tooltip }}
          >
            <HelpOutlineOutlinedIcon />
          </Tooltip>
        </FormGroup>
        {profile?.notifications?.mention?.active === true && (
          <NotificationSettingsSelect notificationResourceType="mention" />
        )}
      </div>
      <div className={classes.pref}>
        <FormGroup row className={classes.form_group}>
          <FormControlLabel
            control={
              <Switch
                checked={
                  profile?.notifications?.observation_plans?.active === true
                }
                name="observation_plans"
                onChange={prefToggled}
              />
            }
            label="Observation Plans"
          />
          <Tooltip
            title="This allows you to be notified for all completed observation plans for which you are an allocation admin."
            placement="right"
            classes={{ tooltip: classes.tooltip }}
          >
            <HelpOutlineOutlinedIcon />
          </Tooltip>
        </FormGroup>
        {profile?.notifications?.observation_plans?.active === true && (
          <NotificationSettingsSelect notificationResourceType="observation_plans" />
        )}
      </div>
    </div>
  );
};

export default NotificationPreferences;
