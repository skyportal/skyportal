import { WidgetProps } from "@rjsf/utils";
import SearchableValueSelect from "./SearchableValueSelect";

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
}: WidgetProps) => (
  <SearchableValueSelect
    id={id}
    multiple={Boolean(multiple)}
    options={options.enumOptions ?? []}
    value={value}
    onChange={(newValue) => onChange(newValue ?? undefined)}
    {...(!hideLabel && { label })}
    {...(placeholder && { placeholder })}
    textFieldProps={{ slotProps: { inputLabel: { required } } }}
    disabled={Boolean(disabled || readonly)}
    error={(rawErrors?.length ?? 0) > 0}
    fullWidth
  />
);

export default SearchableSelectWidget;
