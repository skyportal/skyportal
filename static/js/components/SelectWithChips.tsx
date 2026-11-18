import { useState } from "react";
import { makeStyles } from "tss-react/mui";
import Chip from "@mui/material/Chip";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import RemovableChip from "./RemovableChip";
import SearchableValueSelect from "./SearchableValueSelect";
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

  if (searchable) {
    return (
      <SearchableValueSelect
        id={id}
        label={label}
        multiple
        options={options}
        value={initValue || []}
        onChange={(value) => handleChange({ target: { value } })}
        className={classes.formControl}
      />
    );
  }

  return (
    <FormControl className={classes.formControl}>
      <InputLabel>{label}</InputLabel>
      <Select
        id={id}
        label={label}
        multiple
        value={initValue || []}
        onChange={handleChange}
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
        {options?.map((option) => (
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

const SelectLabelWithChips = ({
  label,
  id,
  initValue = [],
  onChange,
  options,
}: SelectLabelWithChipsProps) => {
  const { classes } = useStyles();
  return (
    <SearchableValueSelect
      id={id}
      label={label}
      multiple
      options={options}
      value={(initValue || []).map((option) => option.id)}
      onChange={(ids) =>
        onChange({
          target: {
            value: ids.map((optionId: any) =>
              options.find((option) => option.id === optionId),
            ),
          },
        })
      }
      className={classes.formControl}
    />
  );
};

interface SelectSingleLabelWithChipsProps {
  label: string;
  id: string;
  initValue?: LabelOption;
  onChange: (...args: any[]) => void;
  options: LabelOption[];
}

const SelectSingleLabelWithChips = ({
  label,
  id,
  initValue,
  onChange,
  options,
}: SelectSingleLabelWithChipsProps) => {
  const { classes } = useStyles();
  return (
    <SearchableValueSelect
      id={id}
      label={label}
      options={options}
      value={initValue?.id ?? null}
      onChange={(optionId) =>
        onChange({
          target: {
            value: options.find((option) => option.id === optionId) ?? "",
          },
        })
      }
      className={classes.formControl}
    />
  );
};

export default SelectWithChips;

export { SelectLabelWithChips, SelectSingleLabelWithChips };
