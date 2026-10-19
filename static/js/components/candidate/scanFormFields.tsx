import { useLayoutEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { Controller } from "react-hook-form";
import type { Control, RegisterOptions } from "react-hook-form";
import Box from "@mui/material/Box";
import Checkbox from "@mui/material/Checkbox";
import Chip from "@mui/material/Chip";
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

export const scanFilters = (filters: any[], groupIDs: number[]) => {
  const available = filters.filter((f) => groupIDs.includes(f.group_id));
  return available.length > new Set(available.map((f) => f.group_id)).size
    ? available
    : [];
};

const moreTags = (count: number) => (
  <Box component="span" sx={{ flexShrink: 0, mx: 0.5 }}>
    +{count}
  </Box>
);

const horizontal = (style: CSSStyleDeclaration, box: "margin" | "padding") =>
  parseFloat(style[`${box}Left`]) + parseFloat(style[`${box}Right`]);

interface CompactTagsProps {
  labels: string[];
  getItemProps: (args: {
    index: number;
  }) => { key?: number } & Record<string, unknown>;
}

const CompactTags = ({ labels, getItemProps }: CompactTagsProps) => {
  const measureRef = useRef<HTMLSpanElement>(null);
  const [shown, setShown] = useState(1);

  useLayoutEffect(() => {
    const root = measureRef.current?.parentElement;
    const chips = measureRef.current?.firstElementChild;
    if (!root || !chips) return undefined;
    const fit = () => {
      const input = root.querySelector("input");
      const tag = root.querySelector("[data-item-index]");
      const inputStyle = input && getComputedStyle(input);
      const free =
        root.clientWidth -
        horizontal(getComputedStyle(root), "padding") -
        (inputStyle
          ? parseFloat(inputStyle.minWidth) +
            horizontal(inputStyle, "padding") +
            horizontal(inputStyle, "margin")
          : 0);
      const needed =
        chips.getBoundingClientRect().width +
        (tag ? 2 * horizontal(getComputedStyle(tag), "margin") : 0);
      setShown(needed <= free ? 2 : 1);
    };
    fit();
    const observer = new ResizeObserver(fit);
    observer.observe(root);
    return () => observer.disconnect();
  });

  const visible = Math.min(shown, labels.length);
  return (
    <>
      {labels.slice(0, visible).map((label, index) => {
        const { key, ...itemProps } = getItemProps({ index });
        return (
          <Chip
            key={key}
            size="small"
            label={label}
            {...itemProps}
            sx={{ minWidth: 0 }}
          />
        );
      })}
      {labels.length > visible && moreTags(labels.length - visible)}
      <Box
        ref={measureRef}
        component="span"
        aria-hidden
        sx={{
          position: "absolute",
          width: 0,
          overflow: "hidden",
          visibility: "hidden",
        }}
      >
        <Box component="span" sx={{ display: "flex", width: "max-content" }}>
          {labels.slice(0, 2).map((label, index) => (
            <Chip key={index} size="small" label={label} onDelete={() => {}} />
          ))}
          {labels.length > 2 && moreTags(labels.length - 2)}
        </Box>
      </Box>
    </>
  );
};

const singleLine = {
  "& .MuiAutocomplete-inputRoot": { flexWrap: "nowrap" },
  "& .MuiAutocomplete-inputRoot:not(.Mui-focused) .MuiAutocomplete-input": {
    minWidth: 8,
    px: 0,
  },
};

type FilterSelectProps = Omit<
  SearchableSelectProps,
  "options" | "value" | "onChange"
> & {
  filters: any[];
  value: number[];
  onChange: (ids: number[]) => void;
};

export const FilterSelect = ({
  filters,
  value,
  onChange,
  sx,
  ...props
}: FilterSelectProps) => (
  <SearchableSelect
    multiple
    disableCloseOnSelect
    label="Filters"
    options={filters}
    isOptionEqualToValue={(o: any, v: any) => o.id === v.id}
    value={filters.filter((f) => value.includes(f.id))}
    onChange={(_event, selected: any[]) => onChange(selected.map((f) => f.id))}
    renderOption={({ key, ...optionProps }, filter: any, { selected }) => (
      <li key={key} {...optionProps}>
        <Checkbox size="small" checked={selected} sx={{ p: 0, mr: 1 }} />
        {filter.name}
      </li>
    )}
    renderValue={(selected: any[], getItemProps) => (
      <CompactTags
        labels={selected.map((f) => f.name)}
        getItemProps={getItemProps}
      />
    )}
    placeholder={value.length > 0 ? "" : "All"}
    sx={[singleLine, ...(Array.isArray(sx) ? sx : [sx])]}
    {...props}
  />
);

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
  sx,
  ...props
}: GroupSelectProps) => (
  <SearchableSelect
    multiple
    disableCloseOnSelect
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
    renderValue={(selected: Group[], getItemProps) => (
      <CompactTags
        labels={selected.map((g) => g.name)}
        getItemProps={getItemProps}
      />
    )}
    sx={[singleLine, ...(Array.isArray(sx) ? sx : [sx])]}
    {...props}
  />
);
