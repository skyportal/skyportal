import { WidgetProps } from "@rjsf/utils";
import SearchableSelect from "./SearchableSelect";

const optionLabel = (option: any) => option.label;
const optionKey = (option: any) => String(option.value);
const sameOption = (option: any, selected: any) =>
  option.value === selected.value;

const SearchableSelectWidget = ({
  id,
  value,
  onChange,
  options,
  multiple,
  label,
  hideLabel,
  placeholder,
  required,
  disabled,
  readonly,
  rawErrors,
}: WidgetProps) => {
  const enumOptions = options.enumOptions ?? [];
  const optionFor = (optionValue: any) =>
    enumOptions.find((option) => option.value === optionValue);
  const selected = multiple
    ? (value ?? []).map(optionFor).filter(Boolean)
    : (optionFor(value) ?? null);

  return (
    <SearchableSelect
      id={id}
      multiple={Boolean(multiple)}
      disableCloseOnSelect={Boolean(multiple)}
      autoHighlight
      limitTags={5}
      options={enumOptions}
      value={selected}
      getOptionLabel={optionLabel}
      getOptionKey={optionKey}
      isOptionEqualToValue={sameOption}
      onChange={(_event: any, newValue: any) =>
        onChange(
          multiple
            ? newValue.map((option: any) => option.value)
            : newValue?.value,
        )
      }
      {...(!hideLabel && { label })}
      {...(placeholder && { placeholder })}
      textFieldProps={{ slotProps: { inputLabel: { required } } }}
      disabled={Boolean(disabled || readonly)}
      error={(rawErrors?.length ?? 0) > 0}
      fullWidth
    />
  );
};

export default SearchableSelectWidget;
