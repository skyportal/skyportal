import type { ReactNode } from "react";
import { Controller } from "react-hook-form";
import type { Control, RegisterOptions } from "react-hook-form";
import Box from "@mui/material/Box";
import Checkbox from "@mui/material/Checkbox";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";
import type { SwitchProps } from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import type { TextFieldProps } from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import { useGetFiltersQuery } from "../../ducks/filter";
import { useGetGroupsQuery } from "../../ducks/groups";
import type { Group } from "../../types";
import FormValidationError from "../FormValidationError";
import SearchableSelect from "../SearchableSelect";
import type { SearchableSelectProps } from "../SearchableSelect";

export const savedStatusSelectOptions = [
  { value: "all", label: "regardless of saved status" },
  { value: "savedToAllSelected", label: "saved to all selected groups" },
  {
    value: "savedToAnySelected",
    label: "saved to at least one of the selected groups",
  },
  {
    value: "savedToAnyAccessible",
    label: "saved to at least one group I have access to",
  },
  {
    value: "notSavedToAnyAccessible",
    label: "not saved to any group I have access to",
  },
  {
    value: "notSavedToAnySelected",
    label: "not saved to any of the selected groups",
  },
  {
    value: "notSavedToAllSelected",
    label: "not saved to all of the selected groups",
  },
];

export const gcnNumberFields = [
  {
    name: "maxSgscore",
    label: "Max star score (sgscore)",
    step: 0.05,
    min: 0,
    max: 1,
  },
  {
    name: "maxCredibleLevel",
    label: "Max credible level",
    step: 0.05,
    min: 0,
    max: 1,
  },
  {
    name: "minDistpsnr",
    label: "Min PS1 distance [arcsec]",
    step: 0.5,
    min: 0,
  },
  { name: "minNdethist", label: "Min detections in history", step: 1, min: 0 },
  {
    name: "minAbsGalacticLatitude",
    label: "Min |galactic latitude| [deg]",
    step: 1,
    min: 0,
    max: 90,
  },
  {
    name: "promptDeltaT",
    label: "Always show within [days] of event",
    step: 0.5,
    min: 0,
  },
  { name: "maxDeltaT", label: "Max days since event", step: 0.5, min: 0 },
];

export const sortingOrderLabels: Record<string, string> = {
  asc: "Ascending",
  desc: "Descending",
};

export const column = { display: "flex", flexDirection: "column", gap: 2.5 };

export const twoColumns = {
  display: "grid",
  gridTemplateColumns: "1fr 1fr",
  gap: 1.5,
};

export const annotationKeys = (info: any, origin: string | null) =>
  origin
    ? (info?.[origin] ?? []).flatMap((annotation: any) =>
        Object.keys(annotation ?? {}),
      )
    : [];

interface SectionProps {
  title: string;
  error?: string | false;
  children: ReactNode;
}

export const Section = ({ title, error, children }: SectionProps) => (
  <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
    <Typography variant="subtitle1" sx={{ fontWeight: "bold" }}>
      {title}
    </Typography>
    {error && <FormValidationError message={error} />}
    {children}
  </Box>
);

type FormTextFieldProps = TextFieldProps & {
  name: string;
  control: Control<any>;
  rules?: RegisterOptions;
};

export const FormTextField = ({
  name,
  control,
  rules,
  ...props
}: FormTextFieldProps) => (
  <Controller
    name={name}
    control={control}
    rules={rules ?? {}}
    render={({ field }) => (
      <TextField size="small" {...field} value={field.value ?? ""} {...props} />
    )}
  />
);

export const SwitchField = ({
  label,
  ...props
}: SwitchProps & { label: string }) => (
  <FormControlLabel
    label={label}
    control={<Switch size="small" {...props} />}
    sx={{ m: 0, gap: 1 }}
  />
);

export const useScanGroups = (selectedIDs: number[]) => {
  const { data: groups } = useGetGroupsQuery();
  const { data: filters = [] } = useGetFiltersQuery();
  return (groups?.userAccessible ?? []).filter(
    (group) =>
      selectedIDs.includes(group.id) ||
      filters.some((f: any) => f.group_id === group.id),
  );
};

type GroupSelectProps = Omit<
  SearchableSelectProps,
  "options" | "value" | "onChange"
> & {
  groups: Group[];
  value: number[];
  onChange: (ids: number[]) => void;
  checkboxTestId: string;
};

export const GroupSelect = ({
  groups,
  value,
  onChange,
  checkboxTestId,
  ...props
}: GroupSelectProps) => (
  <SearchableSelect
    multiple
    disableCloseOnSelect
    limitTags={2}
    label="Groups"
    options={groups}
    value={groups.filter((g) => value.includes(g.id))}
    isOptionEqualToValue={(o: Group, v: Group) => o.id === v.id}
    onChange={(_event, selected: Group[]) =>
      onChange(selected.map((g) => g.id))
    }
    renderOption={({ key, ...optionProps }, group: Group, { selected }) => (
      <li key={key} {...optionProps}>
        <Checkbox
          size="small"
          checked={selected}
          data-testid={`${checkboxTestId}-${group.id}`}
          sx={{ p: 0, mr: 1 }}
        />
        {group.name}
      </li>
    )}
    {...props}
  />
);
