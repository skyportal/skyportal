import { ReactNode, useEffect, useState } from "react";
import { showNotification } from "baselayer/components/Notifications";

import Box from "@mui/material/Box";

import { useAppDispatch } from "../../../types/hooks";
import Button from "../../Button";
import ClassificationSelect from "../../classification/ClassificationSelect";
import { SelectLabelWithChips } from "../../SelectWithChips";
import DeliveryChannels from "../../notifications/DeliveryChannels";
import NotificationCard from "../../notifications/NotificationCard";
import PreferenceOption, {
  PreferenceOptions,
} from "../../notifications/PreferenceOption";
import NotificationGcnEvent from "./NotificationGcnEvent";
import { useGetGroupsQuery } from "../../../ducks/groups";
import {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
} from "../../../ducks/profile";
import { useGetAllocationsApiClassnameQuery } from "../../../ducks/allocations";

interface Option {
  id: number;
  label: string;
}

const byLabel = (a: Option, b: Option) =>
  a.label.toLowerCase() < b.label.toLowerCase() ? -1 : 1;

const allocationOption = (allocation: any): Option => ({
  id: allocation?.id,
  label: `${allocation.instrument?.name} [${allocation?.pi}]`,
});

const toggleOption = (setter: (value: Option[]) => void) => (event: any) => {
  const selected: Option[] = [];
  event.target.value.forEach((item: Option) => {
    const index = selected.findIndex((s) => s?.id === item?.id);
    if (index === -1) {
      selected.push(item);
    } else {
      selected.splice(index, 1);
    }
  });
  setter(selected);
};

const Fields = ({ children }: { children: ReactNode }) => (
  <Box
    sx={{
      display: "flex",
      flexWrap: "wrap",
      alignItems: "center",
      gap: 1.5,
      "& .MuiFormControl-root": { minWidth: "14rem", flex: "1 1 14rem" },
    }}
  >
    {children}
  </Box>
);

const SourcesOptions = () => {
  const dispatch = useAppDispatch();
  const prefs =
    (useGetProfileQuery().data?.preferences["notifications"]?.sources as any) ??
    {};
  const groups = useGetGroupsQuery().data?.userAccessible ?? [];
  const { data: allocations = [] } = useGetAllocationsApiClassnameQuery();
  const [updateUserPreferences] = useUpdateUserPreferencesMutation();
  const [classifications, setClassifications] = useState<any[]>(
    prefs.classifications || [],
  );
  const [selectedGroups, setSelectedGroups] = useState<Option[]>([]);
  const [selectedAllocations, setSelectedAllocations] = useState<Option[]>([]);

  const groupOptions = [...groups]
    .map((group: any) => ({ id: group?.id, label: group?.name }))
    .sort(byLabel);
  const allocationOptions = (allocations || [])
    .map(allocationOption)
    .sort(byLabel);

  useEffect(() => {
    if (selectedGroups.length === 0 && groups.length > 0) {
      setClassifications(prefs.classifications || []);
      setSelectedGroups(
        (prefs.groups || [])
          .map((id: number) => groupOptions.find((group) => group.id === id))
          .filter(Boolean),
      );
    }
  }, [prefs, groups]);

  useEffect(() => {
    if (selectedAllocations.length === 0 && allocations.length > 0) {
      setSelectedAllocations(
        (prefs.allocations || [])
          .map((id: number) =>
            allocations.find((allocation: any) => allocation.id === id),
          )
          .filter(Boolean)
          .map(allocationOption),
      );
    }
  }, [prefs, allocations]);

  const save = () => {
    updateUserPreferences({
      notifications: {
        sources: {
          classifications: [...new Set(classifications)],
          groups: [...new Set(selectedGroups.map((group) => group.id))],
          allocations: [
            ...new Set(selectedAllocations.map((allocation) => allocation.id)),
          ],
        },
      },
    });
    dispatch(showNotification("Sources classifications updated"));
  };

  return (
    <>
      <Fields>
        <ClassificationSelect
          selectedClassifications={classifications}
          setSelectedClassifications={setClassifications}
        />
        {groupOptions.length > 0 && (
          <>
            <SelectLabelWithChips
              label="Groups (optional)"
              id="groups-select"
              initValue={selectedGroups}
              onChange={toggleOption(setSelectedGroups)}
              options={groupOptions}
            />
            <SelectLabelWithChips
              label="Allocations (optional)"
              id="allocations-select"
              initValue={selectedAllocations}
              onChange={toggleOption(setSelectedAllocations)}
              options={allocationOptions}
            />
          </>
        )}
        <Button secondary onClick={save} data-testid="addShortcutButton">
          Update
        </Button>
      </Fields>
      <PreferenceOptions>
        <PreferenceOption
          type="sources"
          field="new_spectra"
          title="New spectra"
          text="Also when a source in these groups gets a new spectrum."
        />
      </PreferenceOptions>
    </>
  );
};

const ExtractionOptions = () => {
  const saved =
    (
      useGetProfileQuery().data?.preferences["notifications"]
        ?.gcn_extractions as any
    )?.classifications ?? [];
  const [updateUserPreferences] = useUpdateUserPreferencesMutation();
  const [classes, setClasses] = useState<string[]>(saved);

  useEffect(() => {
    setClasses(saved);
  }, [saved.join(",")]);

  return (
    <Fields>
      <ClassificationSelect
        selectedClassifications={classes}
        setSelectedClassifications={setClasses}
      />
      <Button
        secondary
        onClick={() =>
          updateUserPreferences({
            notifications: {
              gcn_extractions: { classifications: [...new Set(classes)] },
            },
          })
        }
        data-testid="updateExtractionClassesButton"
      >
        Update
      </Button>
    </Fields>
  );
};

const FavoriteSourcesOptions = () => {
  const prefs =
    (useGetProfileQuery().data?.preferences["notifications"]
      ?.favorite_sources as any) ?? {};
  return (
    <PreferenceOptions>
      <PreferenceOption
        type="favorite_sources"
        field="new_comments"
        title="New comments"
      />
      {prefs.new_comments === true && (
        <PreferenceOption
          type="favorite_sources"
          field="new_bot_comments"
          title="Including bot comments"
        />
      )}
      <PreferenceOption
        type="favorite_sources"
        field="new_spectra"
        title="New spectra"
      />
      <PreferenceOption
        type="favorite_sources"
        field="new_classifications"
        title="New classifications"
      />
      {prefs.new_classifications === true && (
        <PreferenceOption
          type="favorite_sources"
          field="new_ml_classifications"
          title="Including ML classifications"
        />
      )}
    </PreferenceOptions>
  );
};

const NOTIFICATIONS: {
  key: string;
  title: string;
  text: string;
  options?: ReactNode;
}[] = [
  {
    key: "sources",
    title: "Sources",
    text: "When a source gets one of the classifications you pick.",
    options: <SourcesOptions />,
  },
  {
    key: "favorite_sources",
    title: "Favorite sources",
    text: "Activity on the sources in your favorites.",
    options: <FavoriteSourcesOptions />,
  },
  {
    key: "gcn_events",
    title: "GCN events",
    text: "When a GCN event matching one of your profiles gets a new skymap.",
    options: (
      <>
        <PreferenceOptions>
          <PreferenceOption
            type="gcn_events"
            field="new_tags"
            title="New tags"
            text="Also when tags are added to the skymap."
          />
        </PreferenceOptions>
        <NotificationGcnEvent />
      </>
    ),
  },
  {
    key: "gcn_extractions",
    title: "GCN circular extractions",
    text: "When a circular is parsed into a classification. Leave the list empty to hear about all of them.",
    options: <ExtractionOptions />,
  },
  {
    key: "analysis_services",
    title: "Analysis services",
    text: "When an analysis you started is done.",
  },
  {
    key: "facility_transactions",
    title: "Follow-up requests",
    text: "Every facility transaction: follow-up requests and observation plans sent out.",
  },
  {
    key: "observation_plans",
    title: "Observation plans",
    text: "Completed observation plans on allocations you administer.",
  },
  {
    key: "reminders",
    title: "Reminders",
    text: "When your reminders fire.",
    options: (
      <PreferenceOptions>
        <PreferenceOption
          type="reminders"
          field="reminder_on_source"
          title="On sources"
        />
        <PreferenceOption
          type="reminders"
          field="reminder_on_spectra"
          title="On spectra"
        />
        <PreferenceOption
          type="reminders"
          field="reminder_on_gcn"
          title="On GCN events"
        />
        <PreferenceOption
          type="reminders"
          field="reminder_on_shift"
          title="On shifts"
        />
      </PreferenceOptions>
    ),
  },
  {
    key: "mention",
    title: "@ Mentions",
    text: "When someone mentions you in a comment.",
  },
  {
    key: "deployments",
    title: "Deployments",
    text: "Each time a new version is deployed. The history is on the Deployments page.",
  },
];

const NotificationPreferences = () => (
  <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
    <DeliveryChannels />
    {NOTIFICATIONS.map(({ key, title, text, options }) => (
      <NotificationCard key={key} type={key} title={title} text={text}>
        {options}
      </NotificationCard>
    ))}
  </Box>
);

export default NotificationPreferences;
