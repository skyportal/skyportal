import { useState } from "react";
import { Controller, useForm, useWatch } from "react-hook-form";
import { skipToken } from "@reduxjs/toolkit/query";

import Box from "@mui/material/Box";
import MenuItem from "@mui/material/MenuItem";
import SaveIcon from "@mui/icons-material/Save";

import Button from "../Button";
import SearchableSelect from "../SearchableSelect";
import ClassificationSelect from "../classification/ClassificationSelect";
import { useGetAnnotationsInfoQuery } from "../../ducks/candidate/candidates";
import { useGetGroupsQuery } from "../../ducks/groups";
import {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
} from "../../ducks/profile";
import { filterAnnotationOrigins } from "./annotationSortOptions";
import {
  FormTextField,
  GroupSelect,
  Section,
  SwitchField,
  annotationKeys,
  column,
  gcnNumberFields,
  savedStatusSelectOptions,
  sortingOrderLabels,
  twoColumns,
  useScanGroups,
} from "./scanFormFields";

const optionalFields = [
  "timeRange",
  "redshiftMinimum",
  "redshiftMaximum",
  "sortingOrigin",
  "sortingKey",
  "sortingOrder",
  ...gcnNumberFields.map(({ name }) => name),
];

const profileValues = (profile: any) => ({
  name: profile?.name ?? "",
  timeRange: profile?.timeRange ?? "24",
  groupIDs: profile?.groupIDs ?? [],
  savedStatus: profile?.savedStatus ?? "all",
  savedGroupIDs: profile?.savedGroupIDs ?? [],
  rejectedStatus: profile?.rejectedStatus ?? "show",
  redshiftMinimum: profile?.redshiftMinimum ?? "",
  redshiftMaximum: profile?.redshiftMaximum ?? "",
  ...Object.fromEntries(
    gcnNumberFields.map(({ name }) => [name, profile?.[name] ?? ""]),
  ),
  sortingOrigin: profile?.sortingOrigin ?? null,
  sortingKey: profile?.sortingKey ?? null,
  sortingOrder: profile?.sortingOrder ?? null,
});

interface CandidatesPreferencesFormProps {
  editingProfile?: any;
  onClose: () => void;
  selectedScanningProfile?: any;
  setSelectedScanningProfile: (...a: any[]) => void;
}

const CandidatesPreferencesForm = ({
  editingProfile,
  onClose,
  selectedScanningProfile,
  setSelectedScanningProfile,
}: CandidatesPreferencesFormProps) => {
  const profiles: any[] =
    (useGetProfileQuery().data?.preferences as any)?.scanningProfiles ?? [];
  const [updateUserPreferences] = useUpdateUserPreferencesMutation();
  const [selectedClassifications, setSelectedClassifications] = useState<
    string[]
  >(editingProfile?.classifications ?? []);
  const [classificationsWith, setClassificationsWith] = useState(
    editingProfile?.classificationsWith !== false,
  );

  const {
    handleSubmit,
    control,
    getValues,
    reset,
    formState: { errors },
  } = useForm<any>({ defaultValues: profileValues(editingProfile) });
  const [groupIDs, sortingOrigin, savedStatus]: [
    number[],
    string | null,
    string,
  ] = useWatch({
    control,
    name: ["groupIDs", "sortingOrigin", "savedStatus"],
  });
  const scanGroups = useScanGroups(groupIDs);
  const { data: groups } = useGetGroupsQuery();
  const showSavedGroups = savedStatus.endsWith("Selected");
  const { data: availableAnnotationsInfo } = useGetAnnotationsInfoQuery(
    groupIDs.length ? groupIDs : skipToken,
  );
  const resetFields = (values: Record<string, any>) =>
    reset({ ...getValues(), ...values });

  const validateName = (name: string) =>
    Boolean(name) &&
    (name === editingProfile?.name ||
      !profiles.some((profile) => profile.name === name));

  const validateSorting = () => {
    const f = getValues();
    return (
      f.sortingOrigin === null ||
      (f.sortingKey !== null && f.sortingOrder !== null)
    );
  };

  const onSubmit = (formData: any) => {
    const savedGroupIDs = formData.savedGroupIDs.filter((id: number) =>
      groups?.userAccessible?.some((group) => group.id === id),
    );
    const data: any = {
      name: formData.name,
      groupIDs: formData.groupIDs,
      savedStatus: formData.savedStatus,
      ...(showSavedGroups && savedGroupIDs.length > 0 ? { savedGroupIDs } : {}),
      rejectedStatus: formData.rejectedStatus,
      default: editingProfile ? editingProfile.default : true,
    };
    optionalFields.forEach((key) => {
      if (formData[key] !== "" && formData[key] != null) {
        data[key] = formData[key];
      }
    });
    if (selectedClassifications.length > 0) {
      data.classifications = selectedClassifications;
      data.classificationsWith = classificationsWith;
    }

    updateUserPreferences({
      scanningProfiles: editingProfile
        ? profiles.map((profile) =>
            profile.name === editingProfile.name ? data : profile,
          )
        : [
            ...profiles.map((profile) => ({ ...profile, default: false })),
            data,
          ],
    });
    if (
      !editingProfile ||
      selectedScanningProfile?.name === editingProfile.name
    ) {
      setSelectedScanningProfile(data);
    }
    onClose();
  };

  return (
    <Box
      component="form"
      onSubmit={handleSubmit(onSubmit)}
      sx={{ display: "flex", flexDirection: "column", gap: 3, pt: 1 }}
    >
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1.5 }}>
        <FormTextField
          name="name"
          control={control}
          rules={{ validate: validateName }}
          label="Name"
          data-testid="profile-name"
          error={Boolean(errors["name"])}
          helperText={
            errors["name"] ? "Must be unique and at least 1 character" : ""
          }
          sx={{ flex: 1, minWidth: 200 }}
        />
        <FormTextField
          name="timeRange"
          control={control}
          label="Hours before now"
          type="number"
          data-testid="timeRange"
          slotProps={{ htmlInput: { step: 1, min: 1 } }}
          sx={{ width: 150 }}
        />
        <Controller
          name="groupIDs"
          control={control}
          rules={{ validate: (ids: number[]) => ids.length > 0 }}
          render={({ field }) => (
            <GroupSelect
              groups={scanGroups}
              value={field.value}
              onChange={field.onChange}
              checkboxTestId="profileFilteringFormGroupCheckbox"
              error={Boolean(errors["groupIDs"])}
              helperText={
                errors["groupIDs"] ? "Select at least one group." : ""
              }
              textFieldProps={{ "data-testid": "profileGroupSelect" }}
              sx={{ flex: 2, minWidth: 260 }}
            />
          )}
        />
      </Box>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
          gap: 3,
        }}
      >
        <Box sx={column}>
          <Section title="Saved status">
            <FormTextField
              select
              name="savedStatus"
              control={control}
              data-testid="profileSavedStatusSelect"
              fullWidth
            >
              {savedStatusSelectOptions.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </FormTextField>
            {showSavedGroups && (
              <Controller
                name="savedGroupIDs"
                control={control}
                render={({ field: { onChange, value } }) => (
                  <GroupSelect
                    groups={groups?.userAccessible ?? []}
                    value={value}
                    onChange={onChange}
                    label="Saved status groups"
                    checkboxTestId="profileSavedStatusGroupCheckbox"
                    helperText="Defaults to the scanning groups"
                    textFieldProps={{
                      "data-testid": "profileSavedStatusGroupSelect",
                    }}
                  />
                )}
              />
            )}
            <Controller
              name="rejectedStatus"
              control={control}
              render={({ field: { onChange, value } }) => (
                <SwitchField
                  label="Hide rejected candidates"
                  checked={value === "hide"}
                  onChange={(event) =>
                    onChange(event.target.checked ? "hide" : "show")
                  }
                />
              )}
            />
          </Section>
          <Section title="Classifications">
            <ClassificationSelect
              selectedClassifications={selectedClassifications}
              setSelectedClassifications={setSelectedClassifications}
              showShortcuts
            />
            {selectedClassifications.length > 0 && (
              <SwitchField
                label={`${classificationsWith ? "With" : "Without"} these classifications`}
                checked={classificationsWith}
                onChange={(event) =>
                  setClassificationsWith(event.target.checked)
                }
              />
            )}
          </Section>
          <Section title="Redshift">
            <Box sx={twoColumns}>
              <FormTextField
                name="redshiftMinimum"
                control={control}
                label="Minimum"
                type="number"
                data-testid="profile-minimum-redshift"
                slotProps={{ htmlInput: { step: 0.001 } }}
              />
              <FormTextField
                name="redshiftMaximum"
                control={control}
                label="Maximum"
                type="number"
                data-testid="profile-maximum-redshift"
                slotProps={{ htmlInput: { step: 0.001 } }}
              />
            </Box>
          </Section>
        </Box>
        <Box sx={column}>
          <Section title="GCN crossmatch cuts">
            <Box sx={twoColumns}>
              {gcnNumberFields.map(({ name, label, ...htmlInput }) => (
                <FormTextField
                  key={name}
                  name={name}
                  control={control}
                  label={label}
                  type="number"
                  data-testid={`profile-${name}`}
                  slotProps={{ htmlInput }}
                />
              ))}
            </Box>
          </Section>
          <Section
            title="Annotation sorting"
            error={
              Boolean(errors["sortingOrigin"]) &&
              "All sorting fields must be left empty or all filled out"
            }
          >
            <Box sx={twoColumns}>
              <Controller
                name="sortingOrigin"
                control={control}
                rules={{ validate: validateSorting }}
                render={({ field: { onChange, value } }) => (
                  <SearchableSelect
                    id="profileAnnotationSortingOriginSelect"
                    label="Origin"
                    options={Object.keys(availableAnnotationsInfo ?? {})}
                    filterOptions={(options, state) =>
                      filterAnnotationOrigins(options, state.inputValue)
                    }
                    value={value}
                    onChange={(_event, origin) =>
                      origin
                        ? onChange(origin)
                        : resetFields({
                            sortingOrigin: null,
                            sortingKey: null,
                            sortingOrder: null,
                          })
                    }
                  />
                )}
              />
              <Controller
                name="sortingKey"
                control={control}
                render={({ field: { onChange, value } }) => (
                  <SearchableSelect
                    id="profileAnnotationSortingKeySelect"
                    label="Key"
                    options={annotationKeys(
                      availableAnnotationsInfo,
                      sortingOrigin,
                    )}
                    value={value}
                    onChange={(_event, key) => onChange(key)}
                  />
                )}
              />
              <Controller
                name="sortingOrder"
                control={control}
                render={({ field: { onChange, value } }) => (
                  <SearchableSelect
                    id="profileAnnotationSortingOrderSelect"
                    data-testid="profileAnnotationSortingOrderSelect"
                    label="Order"
                    options={["asc", "desc"]}
                    value={value}
                    getOptionLabel={(option) =>
                      sortingOrderLabels[option] ?? "None"
                    }
                    onChange={(_event, order) => onChange(order)}
                  />
                )}
              />
            </Box>
          </Section>
        </Box>
      </Box>
      <Box sx={{ display: "flex", justifyContent: "flex-end", gap: 1 }}>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          primary
          type="submit"
          endIcon={<SaveIcon />}
          data-testid="saveScanningProfileButton"
        >
          Save
        </Button>
      </Box>
    </Box>
  );
};

export default CandidatesPreferencesForm;
