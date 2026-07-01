import { useState } from "react";
import { makeStyles } from "tss-react/mui";
import Chip from "@mui/material/Chip";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
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
}

const SelectWithChips = (props: SelectWithChipsProps) => {
  const { classes } = useStyles();
  const theme = useTheme();
  const [opts, setOpts] = useState<string[]>([]);
  const { label, id, initValue = [], onChange, options } = props;
  const MAX_CHAR = 90;
  const cumSum: number[] = [];

  initValue?.forEach((item, index) => {
    cumSum.push(item?.length + (index > 0 ? (cumSum[index - 1] ?? 0) : 0));
  });

  const max_chips_nb =
    initValue?.length > 0 && !initValue.some((word) => word === undefined)
      ? cumSum.filter((sum) => sum <= MAX_CHAR).length
      : -1;

  return (
    <FormControl className={classes.formControl}>
      <InputLabel>{label}</InputLabel>
      <Select
        id={id}
        label={label}
        multiple
        value={initValue || []}
        onChange={(event: any) => {
          onChange(event);
          setOpts(
            event.target.value.includes("Clear selections")
              ? []
              : event.target.value,
          );
        }}
        renderValue={(selected: any) => (
          <div className={classes.chips}>
            {selected.slice(0, max_chips_nb).map((value: any) => (
              <Chip key={value} label={value} />
            ))}
            {selected.length > max_chips_nb && (
              <Chip label={`+${selected.length - max_chips_nb}`} />
            )}
          </div>
        )}
        MenuProps={menuProps}
      >
        {options?.map((option, index) => (
          <MenuItem
            key={index}
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

  return (
    <FormControl className={classes.formControl}>
      <InputLabel>{label}</InputLabel>
      <Select
        id={id}
        multiple
        label={label}
        value={(initValue || []) as any}
        onChange={(event: any) => {
          onChange(event);
          setOpts(
            event.target.value.includes("Clear selections")
              ? []
              : event.target.value,
          );
        }}
        renderValue={(selected: any) => (
          <div className={classes.chips}>
            {selected.slice(0, max_chips_nb).map((value: any) => (
              <Chip key={value.id} label={value.label} />
            ))}
            {selected.length > max_chips_nb && (
              <Chip label={`+${selected.length - max_chips_nb}`} />
            )}
          </div>
        )}
        MenuProps={menuProps}
      >
        {options?.map((option) => (
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

  return (
    <FormControl className={classes.formControl}>
      <InputLabel>{label}</InputLabel>
      <Select
        id={id}
        label={label}
        value={(initValue || "") as any}
        onChange={(event: any) => onChange(event)}
        renderValue={(selected: any) => <Chip label={selected.label} />}
        MenuProps={menuProps}
      >
        {options?.map((option) => (
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
