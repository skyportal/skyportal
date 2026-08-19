import { useGetGroupsQuery } from "../../../ducks/groups";
import { ReactNode, useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { makeStyles } from "tss-react/mui";
import { showNotification } from "baselayer/components/Notifications";

import FormGroup from "@mui/material/FormGroup";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";
import { useAppDispatch } from "../../../types/hooks";
import Button from "../../Button";

import ClassificationSelect from "../../classification/ClassificationSelect";
import NotificationSettingsSelect from "./NotificationSettingsSelect";
import { Help } from "./PreferencesPanel";
import {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
} from "../../../ducks/profile";
import { useGetAllocationsApiClassnameQuery } from "../../../ducks/allocations";
import NotificationGcnEvent from "./NotificationGcnEvent";
import { SelectLabelWithChips } from "../../SelectWithChips";

const useStyles = makeStyles()((theme) => ({
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
}));

const NOTIFICATIONS = [
  {
    key: "sources",
    label: "Sources",
    tooltip:
      "This allows you to be notified for all sources, based on a certain criteria. For now, you can select classification(s) to be notified for, when added to any source.",
  },
  {
    key: "gcn_events",
    label: "GCN Events",
    tooltip:
      "This allows you to be notified when GCN events receive a new skymap (and optionally when new tags are added to the skymap). You must create at least one notification profile",
  },
  {
    key: "facility_transactions",
    label: "Facility Transactions / Follow-up Requests",
    tooltip:
      "This allows you to be notified for all facility transactions (followup requests, observation plans).",
  },
  {
    key: "analysis_services",
    label: "Analysis Services",
    tooltip:
      "This allows you to be notified for all completed analysis services.",
  },
  {
    key: "favorite_sources",
    label: "Favorite Sources",
    tooltip:
      "This allows you to be notified when certain actions are performed by users on your favorite sources. You can select to be notified about new comments, new classifications and new spectra added to a favorite source.",
  },
  {
    key: "mention",
    label: "@ Mentions",
    tooltip:
      "On SkyPortal, you will always be notified when a user mentions you. If you activate this, it will simply allow you to specify in the settings if you want to also be notified by email, sms and/or slack.",
  },
  {
    key: "observation_plans",
    label: "Observation Plans",
    tooltip:
      "This allows you to be notified for all completed observation plans for which you are an allocation admin.",
  },
  {
    key: "reminders",
    label: "Reminders",
    tooltip:
      "Enable to receive notifications when your reminders fire. Click the settings icon to configure email, SMS, or Slack delivery.",
  },
];

const FAVORITE_SOURCES_TOGGLES = [
  { key: "new_comments", label: "New Comments" },
  { key: "new_spectra", label: "New Spectra" },
  { key: "new_classifications", label: "New Classifications" },
];

const REMINDER_TOGGLES = [
  { key: "reminder_on_source", label: "Sources" },
  { key: "reminder_on_spectra", label: "Spectra" },
  { key: "reminder_on_gcn", label: "GCN Events" },
  { key: "reminder_on_shift", label: "Shifts" },
];

const NotificationPreferences = () => {
  const { classes } = useStyles();
  const { data: profileData } = useGetProfileQuery();
  const profile = (profileData?.preferences ?? {}) as any;
  const groups = useGetGroupsQuery().data?.userAccessible ?? [];
  const { data: allocationListApiClassname = [] } =
    useGetAllocationsApiClassnameQuery();
  const dispatch = useAppDispatch();
  const [updateUserPreferences] = useUpdateUserPreferencesMutation();
  const { handleSubmit } = useForm();
  const [selectedClassifications, setSelectedClassifications] = useState<any[]>(
    profile?.notifications?.sources?.classifications || [],
  );
  const [selectedGroups, setSelectedGroups] = useState<any[]>([]);
  const [selectedAllocations, setSelectedAllocations] = useState<any[]>([]);

  const byLabel = (a: any, b: any) =>
    a.label.toLowerCase() < b.label.toLowerCase() ? -1 : 1;

  const allocationOption = (allocation: any) => ({
    id: allocation?.id,
    label: `${allocation.instrument?.name} [${allocation?.pi}]`,
  });

  // `groups` is frozen RTK Query data, so copy before sorting in place.
  const sortedGroups = [...groups]
    .map((group: any) => ({ id: group?.id, label: group?.name }))
    .sort(byLabel);

  const sortedAllocations = (allocationListApiClassname || [])
    .map(allocationOption)
    .sort(byLabel);

  const onSelectChange = (setter: (value: any[]) => void) => (event: any) => {
    const selected: any[] = [];
    event.target.value.forEach((item: any) => {
      const index = selected.findIndex((s) => s?.id === item?.id);
      if (index === -1) {
        selected.push(item);
      } else {
        selected.splice(index, 1);
      }
    });
    setter(selected);
  };

  useEffect(() => {
    if (selectedGroups.length === 0 && groups?.length > 0) {
      setSelectedClassifications(
        profile?.notifications?.sources?.classifications || [],
      );
      setSelectedGroups(
        (profile?.notifications?.sources?.groups || [])
          .map((groupId: any) => groups.find((g: any) => g.id === groupId))
          .filter((group: any) => group)
          .map((group: any) => ({ id: group.id, label: group.name })),
      );
    }
  }, [profile, groups]);

  useEffect(() => {
    if (
      selectedAllocations.length === 0 &&
      allocationListApiClassname?.length > 0
    ) {
      setSelectedAllocations(
        (profile?.notifications?.sources?.allocations || [])
          .map((allocationId: any) =>
            allocationListApiClassname.find((a: any) => a.id === allocationId),
          )
          .filter((allocation: any) => allocation)
          .map(allocationOption),
      );
    }
  }, [profile, allocationListApiClassname]);

  const prefToggled =
    (section: string, field: string) =>
    (event: any): void => {
      updateUserPreferences({
        notifications: { [section]: { [field]: event.target.checked } },
      });
    };

  const toggle = (
    section: string,
    field: string,
    label: string,
    name: string,
  ) => (
    <FormControlLabel
      key={name}
      control={
        <Switch
          checked={profile?.notifications?.[section]?.[field] === true}
          name={name}
          onChange={prefToggled(section, field)}
        />
      }
      label={label}
    />
  );

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
    updateUserPreferences(prefs);
    setSelectedClassifications([...new Set(selectedClassifications)]);
    setSelectedGroups([...new Set(selectedGroups)]);
    dispatch(showNotification("Sources classifications updated"));
  };

  const details: Record<string, ReactNode> = {
    sources: (
      <FormGroup row className={classes.form_group}>
        <form onSubmit={handleSubmit(onSubmitSources)}>
          <div className={classes.form}>
            <div className={classes.form_group_with_spacing}>
              <ClassificationSelect
                selectedClassifications={selectedClassifications}
                setSelectedClassifications={setSelectedClassifications}
              />
              {sortedGroups?.length > 0 && (
                <>
                  <SelectLabelWithChips
                    label="Groups (optional)"
                    id="groups-select"
                    initValue={selectedGroups}
                    onChange={onSelectChange(setSelectedGroups)}
                    options={sortedGroups}
                  />
                  <SelectLabelWithChips
                    label="Allocations (optional)"
                    id="allocations-select"
                    initValue={selectedAllocations}
                    onChange={onSelectChange(setSelectedAllocations)}
                    options={sortedAllocations}
                  />
                </>
              )}
              {toggle(
                "sources",
                "new_spectra",
                "New spectrum",
                "sources_new_spectra",
              )}
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
      </FormGroup>
    ),
    gcn_events: (
      <>
        <FormGroup row className={classes.form_group}>
          {toggle(
            "gcn_events",
            "new_tags",
            "Notify on new tags",
            "gcn_events_new_tags",
          )}
        </FormGroup>
        <NotificationGcnEvent />
      </>
    ),
    favorite_sources: (
      <div className={classes.form_column}>
        <FormGroup row className={classes.form_group}>
          {FAVORITE_SOURCES_TOGGLES.map(({ key, label }) =>
            toggle("favorite_sources", key, label, `favorite_sources_${key}`),
          )}
        </FormGroup>
        <FormGroup row className={classes.form_group}>
          {profile?.notifications?.favorite_sources?.new_comments === true &&
            toggle(
              "favorite_sources",
              "new_bot_comments",
              "Also on BOT comments?",
              "favorite_sources_new_bot_comments",
            )}
          {profile?.notifications?.favorite_sources?.new_classifications ===
            true &&
            toggle(
              "favorite_sources",
              "new_ml_classifications",
              "Also on ML classifications?",
              "favorite_sources_new_ml_classifications",
            )}
        </FormGroup>
      </div>
    ),
    reminders: (
      <FormGroup row className={classes.form_group}>
        {REMINDER_TOGGLES.map(({ key, label }) =>
          toggle("reminders", key, label, key),
        )}
      </FormGroup>
    ),
  };

  return (
    <div>
      {NOTIFICATIONS.map(({ key, label, tooltip }) => (
        <div className={classes.pref} key={key}>
          <FormGroup row className={classes.form_group}>
            {toggle(key, "active", label, key)}
            <Help text={tooltip} />
          </FormGroup>
          {profile?.notifications?.[key]?.active === true && (
            <>
              {details[key]}
              <NotificationSettingsSelect notificationResourceType={key} />
            </>
          )}
        </div>
      ))}
    </div>
  );
};

export default NotificationPreferences;
