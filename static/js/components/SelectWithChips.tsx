import { useState } from "react";
import { makeStyles } from "tss-react/mui";
import Chip from "@mui/material/Chip";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import RemovableChip from "./RemovableChip";
import { useSelectSearch } from "./SelectSearch";
import { useTheme } from "@mui/material/styles";

const useStyles = makeStyles()(() => ({
  chips: {
    display: "flex",
    flexWrap: "wrap",
  },
  formControl: {
    minWidth: "12rem",
    width: "100%",
  },
}));

const getStyles = (option: any, opts: any[], theme: any) => ({
  fontWeight:
    opts.indexOf(option) === -1
      ? theme.typography.fontWeightRegular
      : theme.typography.fontWeightMedium,
});

const menuProps = { slotProps: { paper: { style: { maxHeight: "20rem" } } } };

interface SelectWithChipsProps {
  label: string;
  id: string;
  initValue?: string[];
  onChange: (...args: any[]) => void;
  options: string[];
  searchable?: boolean;
}

const SelectWithChips = (props: SelectWithChipsProps) => {
  const { classes } = useStyles();
  const theme = useTheme();
  const [opts, setOpts] = useState<string[]>([]);
  const {
    label,
    id,
    initValue = [],
    onChange,
    options,
    searchable = false,
  } = props;
  const { searchHeader, matches, resetSearch } = useSelectSearch(
    `${id}-search`,
  );
  const displayedOptions = searchable
    ? options.filter((option) => matches(option) || initValue?.includes(option))
    : options;
  const MAX_CHAR = 90;
  const cumSum: number[] = [];

  initValue?.forEach((item, index) => {
    cumSum.push(item?.length + (index > 0 ? (cumSum[index - 1] ?? 0) : 0));
  });

  const max_chips_nb =
    initValue?.length > 0 && !initValue.some((word) => word === undefined)
      ? cumSum.filter((sum) => sum <= MAX_CHAR).length
      : -1;

  const handleChange = (event: any) => {
    onChange(event);
    setOpts(
      event.target.value.includes("Clear selections") ? [] : event.target.value,
    );
  };

  return (
    <FormControl className={classes.formControl}>
      <InputLabel>{label}</InputLabel>
      <Select
        id={id}
        label={label}
        multiple
        value={initValue || []}
        onChange={handleChange}
        onClose={resetSearch}
        renderValue={(selected: any) => (
          <div className={classes.chips}>
            {selected.slice(0, max_chips_nb).map((value: any) => (
              <RemovableChip
                size="small"
                key={value}
                label={value}
                onDelete={() =>
                  handleChange({
                    target: {
                      value: selected.filter((v: any) => v !== value),
                    },
                  })
                }
              />
            ))}
            {selected.length > max_chips_nb && (
              <Chip size="small" label={`+${selected.length - max_chips_nb}`} />
            )}
          </div>
        )}
        MenuProps={menuProps}
      >
        {searchable && searchHeader}
        {displayedOptions?.map((option) => (
          <MenuItem
            key={option}
            value={option}
            style={getStyles(option, opts, theme)}
          >
            {option}
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
};

interface LabelOption {
  id: string | number;
  label: string;
}

interface SelectLabelWithChipsProps {
  label: string;
  id: string;
  initValue?: LabelOption[];
  onChange: (...args: any[]) => void;
  options: LabelOption[];
}

const SelectLabelWithChips = (props: SelectLabelWithChipsProps) => {
  // the difference with SelectWithChips is that the initValue is not a list of strings, but a list of element with an id and a label
  const { classes } = useStyles();
  const theme = useTheme();
  const [opts, setOpts] = useState<any[]>([]);
  const { label, id, initValue = [], onChange, options } = props;
  const { searchHeader, matches, resetSearch } = useSelectSearch(
    `${id}-search`,
  );
  const MAX_CHAR = 90;
  const cumSum: number[] = [];
  const labels = initValue?.map((item) => item.label);

  labels?.forEach((item, index) => {
    cumSum.push(item?.length + (index > 0 ? (cumSum[index - 1] ?? 0) : 0));
  });

  const max_chips_nb =
    labels?.length > 0 && !labels.some((word) => word === undefined)
      ? cumSum.filter((sum) => sum <= MAX_CHAR).length
      : -1;

  const handleChange = (event: any) => {
    onChange(event);
    setOpts(
      event.target.value.includes("Clear selections") ? [] : event.target.value,
    );
  };

  return (
    <FormControl className={classes.formControl}>
      <InputLabel>{label}</InputLabel>
      <Select
        id={id}
        multiple
        label={label}
        value={(initValue || []) as any}
        onChange={handleChange}
        onClose={resetSearch}
        renderValue={(selected: any) => (
          <div className={classes.chips}>
            {selected.slice(0, max_chips_nb).map((value: any) => (
              <RemovableChip
                size="small"
                key={value.id}
                label={value.label}
                onDelete={() =>
                  handleChange({
                    target: {
                      value: selected.filter((v: any) => v.id !== value.id),
                    },
                  })
                }
              />
            ))}
            {selected.length > max_chips_nb && (
              <Chip size="small" label={`+${selected.length - max_chips_nb}`} />
            )}
          </div>
        )}
        MenuProps={menuProps}
      >
        {searchHeader}
        {options
          ?.filter(
            (option) =>
              matches(option.label) ||
              initValue?.some((selected) => selected.id === option.id),
          )
          .map((option) => (
            <MenuItem
              key={option.id}
              value={option as any}
              style={getStyles(option, opts, theme)}
            >
              {option.label}
            </MenuItem>
          ))}
      </Select>
    </FormControl>
  );
};

interface SelectSingleLabelWithChipsProps {
  label: string;
  id: string;
  initValue?: LabelOption;
  onChange: (...args: any[]) => void;
  options: LabelOption[];
}

const SelectSingleLabelWithChips = (props: SelectSingleLabelWithChipsProps) => {
  // the difference with SelectWithChips is that the initValue is not a list of strings, but a list of element with an id and a label
  const { classes } = useStyles();
  const theme = useTheme();
  const opts: any[] = [];
  const { label, id, initValue = {} as LabelOption, onChange, options } = props;
  const { searchHeader, matches, resetSearch } = useSelectSearch(
    `${id}-search`,
  );

  return (
    <FormControl className={classes.formControl}>
      <InputLabel>{label}</InputLabel>
      <Select
        id={id}
        label={label}
        value={(initValue || "") as any}
        onChange={(event: any) => onChange(event)}
        onClose={resetSearch}
        renderValue={(selected: any) => (
          <Chip size="small" label={selected.label} />
        )}
        MenuProps={menuProps}
      >
        {searchHeader}
        {options
          ?.filter(
            (option) => matches(option.label) || option.id === initValue?.id,
          )
          .map((option) => (
            <MenuItem
              key={option.id}
              value={option as any}
              style={getStyles(option, opts, theme)}
            >
              {option.label}
            </MenuItem>
          ))}
      </Select>
    </FormControl>
  );
};

export default SelectWithChips;

export { SelectLabelWithChips, SelectSingleLabelWithChips };
