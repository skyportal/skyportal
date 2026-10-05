import { useEffect, useRef, useState } from "react";
import { Controller, useForm, useWatch } from "react-hook-form";
import type { Control, FieldErrors } from "react-hook-form";
import { skipToken } from "@reduxjs/toolkit/query";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import Box from "@mui/material/Box";
import Checkbox from "@mui/material/Checkbox";
import Collapse from "@mui/material/Collapse";
import FormControlLabel from "@mui/material/FormControlLabel";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import RestartAltIcon from "@mui/icons-material/RestartAlt";
import SearchIcon from "@mui/icons-material/Search";
import { DateTimePicker } from "@mui/x-date-pickers/DateTimePicker";

import { pickParams } from "../../API";
import { useAppDispatch } from "../../types/hooks";
import type { Group } from "../../types";
import {
  setCandidatesAnnotationSortOptions,
  useGetAnnotationsInfoQuery,
} from "../../ducks/candidate/candidates";
import { useGetFiltersQuery } from "../../ducks/filter";
import { useGetGcnEventsQuery } from "../../ducks/gcnEvents";
import { useGetGroupsQuery } from "../../ducks/groups";
import { useGetProfileQuery } from "../../ducks/profile";
import Button from "../Button";
import FormValidationError from "../FormValidationError";
import SearchableSelect from "../SearchableSelect";
import ClassificationSelect from "../classification/ClassificationSelect";
import CandidatesPreferences from "./CandidatesPreferences";
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

dayjs.extend(utc);

const sameForOneGroup = ["savedToAllSelected", "notSavedToAllSelected"];

const GCN_CROSSMATCH_ORIGIN = "GCN-crossmatch";

const isFilled = (value: any) => value !== "" && value != null;

const defaultDates = (timeRange?: string) => {
  const endDate = new Date();
  endDate.setSeconds(0, 0);
  const startDate = new Date(endDate);
  if (timeRange)
    startDate.setHours(startDate.getHours() - parseInt(timeRange, 10));
  else startDate.setDate(startDate.getDate() - 1);
  return { startDate, endDate: timeRange ? endDate : null };
};

const formValues = (profile: any) => ({
  ...defaultDates(profile?.timeRange),
  groupIDs: profile?.groupIDs || [],
  filterIDs: [],
  savedStatus: profile?.savedStatus || "all",
  rejectedStatus: profile?.rejectedStatus || "show",
  redshiftMinimum: profile?.redshiftMinimum || "",
  redshiftMaximum: profile?.redshiftMaximum || "",
  classifications: profile?.classifications || [],
  classificationsWith: profile?.classificationsWith !== false,
  ...Object.fromEntries(
    gcnNumberFields.map(({ name }) => [name, profile?.[name] ?? ""]),
  ),
  gcneventid: "",
  localizationid: "",
  localizationCumprob: 0.95,
  firstDetectionAfter: "",
  lastDetectionBefore: "",
  numberDetections: 1,
  requireDetections: true,
  excludeForcedPhotometry: false,
  filterOrigin: null,
  filterKey: null,
  filterValue: "",
  filterMin: "",
  filterMax: "",
  sortingOrigin: profile?.sortingOrigin || null,
  sortingKey: profile?.sortingKey || null,
  sortingOrder: profile?.sortingOrder || null,
});

// "true"/"false" become booleans: the endpoint casts the stored value to boolean for those.
const buildAnnotationFilter = (f: any) => {
  if (!f.filterOrigin || !f.filterKey) return null;
  const filter = { origin: f.filterOrigin, key: f.filterKey };
  if (isFilled(f.filterValue)) {
    const value = String(f.filterValue);
    const lowered = value.trim().toLowerCase();
    const parsed =
      lowered === "true" ? true : lowered === "false" ? false : value;
    return JSON.stringify({ ...filter, value: parsed });
  }
  return isFilled(f.filterMin) && isFilled(f.filterMax)
    ? JSON.stringify({
        ...filter,
        min: String(f.filterMin),
        max: String(f.filterMax),
      })
    : null;
};

interface FormCheckboxProps {
  name: string;
  control: Control<any>;
  label: string;
  tooltip: string;
}

const FormCheckbox = ({ name, control, label, tooltip }: FormCheckboxProps) => (
  <Tooltip title={tooltip}>
    <FormControlLabel
      label={label}
      control={
        <Controller
          name={name}
          control={control}
          render={({ field }) => (
            <Checkbox
              checked={Boolean(field.value)}
              onChange={(event) => field.onChange(event.target.checked)}
            />
          )}
        />
      }
    />
  </Tooltip>
);

interface FilterCandidateListProps {
  setFilterGroups: (groups: Group[]) => void;
  numPerPage: number;
  setSearchParams: (params: Record<string, any>) => void;
}

const FilterCandidateList = ({
  setFilterGroups,
  numPerPage,
  setSearchParams,
}: FilterCandidateListProps) => {
  const dispatch = useAppDispatch();
  const { data: allFilters = [] } = useGetFiltersQuery();
  const { data: groups } = useGetGroupsQuery();
  const userAccessibleGroups = groups?.userAccessible ?? [];
  const { data: userProfile } = useGetProfileQuery();
  const { scanningProfiles = [], useAMPM } = (userProfile?.preferences ??
    {}) as any;
  const defaultScanningProfile = scanningProfiles.find(
    (profile: any) => profile.default,
  );

  const [selectedScanningProfile, setSelectedScanningProfile] = useState<any>(
    defaultScanningProfile,
  );
  const [gcnEventsParams, setGcnEventsParams] = useState<Record<string, any>>(
    {},
  );
  const [moreFiltersOpen, setMoreFiltersOpen] = useState(false);
  const [searchCount, setSearchCount] = useState(0);

  const [gcnEvent, setGcnEvent] = useState<any>(null);
  const { data: gcnEvents } = useGetGcnEventsQuery(gcnEventsParams) as {
    data: any;
  };

  const {
    handleSubmit,
    getValues,
    control,
    reset,
    formState: { errors },
  } = useForm<any>({ defaultValues: formValues(selectedScanningProfile) });
  const resetFields = (values: Record<string, any>) =>
    reset({ ...getValues(), ...values });

  const values = useWatch({ control });
  const groupIDs: number[] = values.groupIDs ?? [];
  const scanGroups = useScanGroups(groupIDs);
  const availableFilters = allFilters.filter((f: any) =>
    groupIDs.includes(f.group_id),
  );
  const showFilterSelect =
    availableFilters.length >
    new Set(availableFilters.map((f: any) => f.group_id)).size;
  const { data: availableAnnotationsInfo } = useGetAnnotationsInfoQuery(
    groupIDs.length ? groupIDs : skipToken,
  );
  const showCrossmatchCuts =
    Boolean(availableAnnotationsInfo?.[GCN_CROSSMATCH_ORIGIN]) ||
    gcnNumberFields.some(({ name }) => isFilled(values[name]));
  const savedStatusOptions = savedStatusSelectOptions.filter(
    ({ value }) =>
      groupIDs.length !== 1 ||
      !sameForOneGroup.includes(value) ||
      value === values.savedStatus,
  );
  const annotationOrigins = Object.keys(availableAnnotationsInfo ?? {});
  const activeFilterCount = [
    values.savedStatus !== "all",
    values.rejectedStatus === "hide",
    values.classifications?.length > 0,
    isFilled(values.redshiftMinimum) || isFilled(values.redshiftMaximum),
    isFilled(values.gcneventid),
    gcnNumberFields.some(({ name }) => isFilled(values[name])),
    isFilled(values.filterOrigin),
    isFilled(values.sortingOrigin),
  ].filter(Boolean).length;

  const selectGroups = (ids: number[]) =>
    setFilterGroups(
      userAccessibleGroups.filter((group) => ids.includes(group.id)),
    );

  const resetForm = () => {
    reset(formValues(selectedScanningProfile));
    setGcnEvent(null);
    selectGroups(selectedScanningProfile?.groupIDs || []);
  };

  // An edit replaces every profile with a copy, so keep the one already loaded.
  useEffect(() => {
    setSelectedScanningProfile(
      (current: any) => current || defaultScanningProfile,
    );
  }, [defaultScanningProfile]);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(resetForm, [selectedScanningProfile]);

  useEffect(() => {
    selectGroups(getValues("groupIDs"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [groups]);

  const selectGcnEvent = (event: any) => {
    const dateobs = event && dayjs.utc(event.dateobs);
    setGcnEvent(event);
    resetFields({
      gcneventid: event?.id ?? "",
      localizationid: event?.localizations[0]?.id ?? "",
      firstDetectionAfter: dateobs ? dateobs.format("YYYY-MM-DD HH:mm:ss") : "",
      lastDetectionBefore: dateobs
        ? dateobs.add(7, "day").format("YYYY-MM-DD HH:mm:ss")
        : "",
      numberDetections: 1,
      localizationCumprob: 0.95,
    });
  };

  const validateDates = () => {
    const { startDate, endDate } = getValues();
    return !startDate || !endDate || startDate <= endDate;
  };

  const validateAnnotationFilter = () => {
    const f = getValues();
    if (!f.filterOrigin) return true;
    if (!f.filterKey) return false;
    return isFilled(f.filterValue)
      ? !isFilled(f.filterMin) && !isFilled(f.filterMax)
      : isFilled(f.filterMin) && isFilled(f.filterMax);
  };

  const validateSorting = () => {
    const f = getValues();
    return (
      f.sortingOrigin === null ||
      (f.sortingKey !== null && f.sortingOrder !== null)
    );
  };

  const onSubmit = (formData: any) => {
    const filterIDs = showFilterSelect
      ? formData.filterIDs.filter((id: number) =>
          availableFilters.some((f: any) => f.id === id),
        )
      : [];
    const sorting = formData.sortingOrigin
      ? {
          origin: formData.sortingOrigin,
          key: formData.sortingKey,
          order: formData.sortingOrder,
        }
      : null;
    dispatch(setCandidatesAnnotationSortOptions(sorting));
    setSearchCount(searchCount + 1);
    setMoreFiltersOpen(false);
    selectGroups(
      filterIDs.length > 0
        ? availableFilters
            .filter((f: any) => filterIDs.includes(f.id))
            .map((f: any) => f.group_id)
        : formData.groupIDs,
    );
    setSearchParams({
      pageNumber: 1,
      numPerPage,
      savedStatus: formData.savedStatus,
      ...(filterIDs.length > 0
        ? { filterIDs }
        : { groupIDs: formData.groupIDs }),
      listNameReject:
        formData.rejectedStatus === "hide" ? "rejected_candidates" : undefined,
      startDate: formData.startDate?.toISOString(),
      endDate: formData.endDate?.toISOString(),
      [formData.classificationsWith
        ? "classifications"
        : "classificationsReject"]: formData.classifications,
      minRedshift: formData.redshiftMinimum,
      maxRedshift: formData.redshiftMaximum,
      ...pickParams(
        formData,
        gcnNumberFields.map(({ name }) => name),
      ),
      ...((formData.gcneventid || formData.localizationid) && {
        localizationDateobs: gcnEvent?.dateobs,
        localizationName: gcnEvent?.localizations?.find(
          (l: any) => l.id === formData.localizationid,
        )?.localization_name,
        ...pickParams(formData, [
          "localizationCumprob",
          "firstDetectionAfter",
          "lastDetectionBefore",
          "numberDetections",
          "requireDetections",
          "excludeForcedPhotometry",
        ]),
      }),
      sortByAnnotationOrigin: sorting?.origin,
      sortByAnnotationKey: sorting?.key,
      sortByAnnotationOrder: sorting?.order,
      annotationFilterList: buildAnnotationFilter(formData),
      _searchCount: searchCount + 1,
    });
  };

  const onInvalid = (invalid: FieldErrors) => {
    if (
      invalid["filterOrigin"] ||
      invalid["sortingOrigin"] ||
      invalid["sortingKey"]
    )
      setMoreFiltersOpen(true);
  };

  const submit = handleSubmit(onSubmit, onInvalid);

  const autoSearched = useRef(false);
  useEffect(() => {
    if (autoSearched.current || !groups || !userProfile) return;
    if (selectedScanningProfile !== defaultScanningProfile) return;
    autoSearched.current = true;
    if (defaultScanningProfile?.groupIDs?.length) submit();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [groups, userProfile, selectedScanningProfile]);

  return (
    <>
      <Paper
        component="form"
        variant="outlined"
        onSubmit={submit}
        sx={{ p: 1.5, pb: 0.5 }}
      >
        <Box
          sx={{
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            gap: 1.5,
          }}
        >
          {scanningProfiles.length > 0 && (
            <TextField
              select
              size="small"
              label="Scanning profile"
              data-testid="scanningProfileSelect"
              value={selectedScanningProfile?.name ?? ""}
              onChange={(event) =>
                setSelectedScanningProfile(
                  scanningProfiles.find(
                    (p: any) => p.name === event.target.value,
                  ) ?? null,
                )
              }
              sx={{ width: 170 }}
            >
              <MenuItem value="">None</MenuItem>
              {scanningProfiles.map((profile: any) => (
                <MenuItem key={profile.name} value={profile.name}>
                  {profile.name}
                </MenuItem>
              ))}
            </TextField>
          )}
          {[
            ["startDate", "Start (Local Time)"],
            ["endDate", "End (Local Time)"],
          ].map(([name, label]) => (
            <Controller
              key={name}
              name={name as string}
              control={control}
              rules={{ validate: validateDates }}
              render={({ field: { onChange, value } }) => (
                <DateTimePicker
                  value={value}
                  onChange={(newValue: Date | null) => {
                    newValue?.setSeconds(0, 0);
                    onChange(newValue);
                  }}
                  label={label}
                  ampm={useAMPM}
                  slotProps={{
                    textField: {
                      size: "small",
                      error: Boolean(errors["startDate"] || errors["endDate"]),
                      sx: { width: 225 },
                    },
                  }}
                />
              )}
            />
          ))}
          <Controller
            name="groupIDs"
            control={control}
            render={({ field }) => (
              <GroupSelect
                groups={scanGroups}
                value={field.value}
                onChange={(ids) => {
                  field.onChange(ids);
                  selectGroups(ids);
                }}
                checkboxTestId="filteringFormGroupCheckbox"
                textFieldProps={{ "data-testid": "scanGroupSelect" }}
                sx={{ flex: 2, minWidth: 280 }}
              />
            )}
          />
          {showFilterSelect && (
            <Controller
              name="filterIDs"
              control={control}
              render={({ field: { onChange, value } }) => (
                <SearchableSelect
                  multiple
                  options={availableFilters}
                  getOptionLabel={(option: any) => option?.name ?? ""}
                  isOptionEqualToValue={(o: any, v: any) => o.id === v.id}
                  value={availableFilters.filter((f: any) =>
                    value.includes(f.id),
                  )}
                  onChange={(_event, newValue: any) =>
                    onChange(newValue.map((f: any) => f.id))
                  }
                  label="Filters"
                  placeholder={value.length > 0 ? "" : "All"}
                  textFieldProps={{ "data-testid": "scanFilterSelect" }}
                  sx={{ flex: 1, minWidth: 160 }}
                />
              )}
            />
          )}
          <Button primary type="submit" endIcon={<SearchIcon />}>
            Search
          </Button>
        </Box>
        <Box sx={{ display: "flex", gap: 1, mt: 0.5 }}>
          <Button
            size="small"
            onClick={() => setMoreFiltersOpen(!moreFiltersOpen)}
            endIcon={moreFiltersOpen ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            aria-expanded={moreFiltersOpen}
            data-testid="scanFiltersButton"
          >
            More filters{activeFilterCount > 0 && ` (${activeFilterCount})`}
          </Button>
          <CandidatesPreferences
            hasProfiles={scanningProfiles.length > 0}
            selectedScanningProfile={selectedScanningProfile}
            setSelectedScanningProfile={setSelectedScanningProfile}
          />
        </Box>
        <Collapse in={moreFiltersOpen} data-testid="scanFiltersPanel">
          <Box
            sx={{
              mt: 0.5,
              pt: 2,
              borderTop: 1,
              borderColor: "divider",
              display: "grid",
              gridTemplateColumns: {
                xs: "1fr",
                md: "1fr 1fr",
                lg: "1fr 1fr 1fr",
              },
              gap: 3,
            }}
          >
            <Box sx={column}>
              <Section title="Saved status">
                <FormTextField
                  select
                  name="savedStatus"
                  control={control}
                  data-testid="savedStatusSelect"
                  fullWidth
                >
                  {savedStatusOptions.map((option) => (
                    <MenuItem key={option.value} value={option.value}>
                      {option.label}
                    </MenuItem>
                  ))}
                </FormTextField>
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
                      data-testid="rejectedStatusSelect"
                    />
                  )}
                />
              </Section>
              <Section title="Classifications">
                <Controller
                  name="classifications"
                  control={control}
                  render={({ field: { onChange, value } }) => (
                    <ClassificationSelect
                      selectedClassifications={value}
                      setSelectedClassifications={onChange}
                      showShortcuts
                    />
                  )}
                />
                {values.classifications?.length > 0 && (
                  <Controller
                    name="classificationsWith"
                    control={control}
                    render={({ field: { onChange, value } }) => (
                      <SwitchField
                        label={`${value ? "With" : "Without"} these classifications`}
                        checked={value}
                        onChange={(event) => onChange(event.target.checked)}
                      />
                    )}
                  />
                )}
              </Section>
              <Section title="Redshift">
                <Box sx={twoColumns}>
                  {[
                    ["redshiftMinimum", "minimum-redshift", "Minimum"],
                    ["redshiftMaximum", "maximum-redshift", "Maximum"],
                  ].map(([name, id, label]) => (
                    <FormTextField
                      key={name}
                      name={name as string}
                      control={control}
                      id={id}
                      label={label}
                      type="number"
                      slotProps={{
                        htmlInput: { step: 0.001 },
                        inputLabel: { shrink: true },
                      }}
                    />
                  ))}
                </Box>
              </Section>
            </Box>
            <Box sx={column}>
              <Section title="GCN event">
                <SearchableSelect
                  id="gcn-event-filtering"
                  label="Dateobs/Name"
                  options={gcnEvents?.events || []}
                  getOptionLabel={(option: any) =>
                    `${option?.dateobs}${option?.aliases?.length > 0 ? ` (${option.aliases})` : ""}`
                  }
                  onInputChange={(event, value) => {
                    const typed =
                      ["change", "clear"].includes(event?.type) && value;
                    const cleared = event?.type === "click" && value === "";
                    if (typed || cleared)
                      setGcnEventsParams({ partialdateobs: value });
                  }}
                  value={gcnEvent}
                  isOptionEqualToValue={(o: any, v: any) => o.id === v.id}
                  onChange={(_event, newValue: any) => selectGcnEvent(newValue)}
                />
                {gcnEvent && (
                  <>
                    <Box sx={twoColumns}>
                      <FormTextField
                        select
                        name="localizationid"
                        control={control}
                        label="Localization"
                      >
                        {gcnEvent.localizations?.map((localization: any) => (
                          <MenuItem
                            value={localization.id}
                            key={localization.id}
                          >
                            {localization.localization_name}
                          </MenuItem>
                        ))}
                      </FormTextField>
                      <FormTextField
                        name="localizationCumprob"
                        control={control}
                        id="cumprob"
                        label="Cumulative Probability"
                        type="number"
                        slotProps={{
                          htmlInput: { step: 0.01, min: 0, max: 1 },
                        }}
                      />
                      <FormTextField
                        name="firstDetectionAfter"
                        control={control}
                        label="First Detection After (UTC)"
                        slotProps={{ inputLabel: { shrink: true } }}
                      />
                      <FormTextField
                        name="lastDetectionBefore"
                        control={control}
                        label="Last Detection Before (UTC)"
                        slotProps={{ inputLabel: { shrink: true } }}
                      />
                      <FormTextField
                        name="numberDetections"
                        control={control}
                        id="minNbDect"
                        label="Minimum Number of Detections"
                        type="number"
                        slotProps={{ htmlInput: { step: 1, min: 1 } }}
                      />
                    </Box>
                    <Box>
                      <FormCheckbox
                        name="requireDetections"
                        control={control}
                        label="Require detections"
                        tooltip="If unchecked, ignore all constraints on detections."
                      />
                      <FormCheckbox
                        name="excludeForcedPhotometry"
                        control={control}
                        label="Ignore Forced Photometry"
                        tooltip="If checked, do not account for forced photometry when applying detections constraints"
                      />
                    </Box>
                  </>
                )}
              </Section>
              {showCrossmatchCuts && (
                <Section title="GCN crossmatch cuts">
                  <Box sx={twoColumns}>
                    {gcnNumberFields.map(({ name, label, ...htmlInput }) => (
                      <FormTextField
                        key={name}
                        name={name}
                        control={control}
                        id={name}
                        label={label}
                        type="number"
                        slotProps={{ htmlInput }}
                      />
                    ))}
                  </Box>
                </Section>
              )}
            </Box>
            <Box sx={column}>
              <Section
                title="Annotation filtering"
                error={
                  Boolean(errors["filterOrigin"]) &&
                  "Choose an origin and key, then either a value or both bounds"
                }
              >
                <Box sx={twoColumns}>
                  <Controller
                    name="filterOrigin"
                    control={control}
                    rules={{ validate: validateAnnotationFilter }}
                    render={({ field: { onChange, value } }) => (
                      <SearchableSelect
                        id="annotationFilteringOriginSelect"
                        label="Origin"
                        data-testid="annotationFilteringOriginSelect"
                        options={annotationOrigins}
                        filterOptions={(options, state) =>
                          filterAnnotationOrigins(options, state.inputValue)
                        }
                        value={value}
                        onChange={(_event, origin) =>
                          origin
                            ? onChange(origin)
                            : resetFields({
                                filterOrigin: null,
                                filterKey: null,
                                filterValue: "",
                                filterMin: "",
                                filterMax: "",
                              })
                        }
                      />
                    )}
                  />
                  <Controller
                    name="filterKey"
                    control={control}
                    render={({ field: { onChange, value } }) => (
                      <SearchableSelect
                        id="annotationFilteringKeySelect"
                        label="Key"
                        data-testid="annotationFilteringKeySelect"
                        options={annotationKeys(
                          availableAnnotationsInfo,
                          values.filterOrigin,
                        )}
                        value={value}
                        onChange={(_event, key) => onChange(key)}
                      />
                    )}
                  />
                </Box>
                <Tooltip title="Exact match. Use true or false for a boolean; leave blank to filter on a numeric range instead.">
                  <Box>
                    <FormTextField
                      name="filterValue"
                      control={control}
                      id="annotationFilteringValue"
                      label="Value"
                      fullWidth
                    />
                  </Box>
                </Tooltip>
                <Box sx={twoColumns}>
                  <FormTextField
                    name="filterMin"
                    control={control}
                    id="annotationFilteringMin"
                    label="Min"
                    type="number"
                  />
                  <FormTextField
                    name="filterMax"
                    control={control}
                    id="annotationFilteringMax"
                    label="Max"
                    type="number"
                  />
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
                        id="annotationSortingOriginSelect"
                        label="Origin"
                        data-testid="annotationSortingOriginSelect"
                        options={annotationOrigins}
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
                    rules={{ validate: validateSorting }}
                    render={({ field: { onChange, value } }) => (
                      <SearchableSelect
                        id="annotationSortingKeySelect"
                        label="Key"
                        data-testid="annotationSortingKeySelect"
                        options={annotationKeys(
                          availableAnnotationsInfo,
                          values.sortingOrigin,
                        )}
                        value={value}
                        onChange={(_event, key) => {
                          if (key === null)
                            resetFields({
                              sortingKey: null,
                              sortingOrder: null,
                            });
                          else if (getValues("sortingOrder") === null)
                            resetFields({
                              sortingKey: key,
                              sortingOrder: "asc",
                            });
                          else onChange(key);
                        }}
                      />
                    )}
                  />
                  <Controller
                    name="sortingOrder"
                    control={control}
                    render={({ field: { onChange, value } }) => (
                      <SearchableSelect
                        id="annotationSortingOrderSelect"
                        label="Order"
                        data-testid="annotationSortingOrderSelect"
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
          <Box sx={{ display: "flex", justifyContent: "flex-end", mt: 1 }}>
            <Tooltip title="Reset all filters and search parameters to default (or selected profile)">
              <Button onClick={resetForm} endIcon={<RestartAltIcon />}>
                Reset
              </Button>
            </Tooltip>
          </Box>
        </Collapse>
      </Paper>
      {(errors["startDate"] || errors["endDate"]) && (
        <FormValidationError message="Invalid date range." />
      )}
    </>
  );
};

export default FilterCandidateList;
