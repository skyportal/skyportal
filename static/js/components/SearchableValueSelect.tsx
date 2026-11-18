import { ReactNode } from "react";
import SearchableSelect, { SearchableSelectProps } from "./SearchableSelect";

const defaultOptionValue = (option: any) =>
  option?.value ?? option?.id ?? option;
const defaultOptionLabel = (option: any) =>
  String(option?.label ?? option?.name ?? option ?? "");

export type SearchableValueSelectProps = Omit<
  SearchableSelectProps,
  "options" | "value" | "onChange" | "getOptionLabel" | "multiple"
> & {
  options: any[];
  value: any;
  onChange: (value: any) => void;
  multiple?: boolean;
  getOptionValue?: (option: any) => any;
  getOptionLabel?: (option: any) => string;
  renderOptionContent?: (option: any) => ReactNode;
};

const SearchableValueSelect = ({
  options,
  value,
  onChange,
  multiple = false,
  getOptionValue = defaultOptionValue,
  getOptionLabel = defaultOptionLabel,
  renderOptionContent,
  limitTags = 5,
  ...props
}: SearchableValueSelectProps) => {
  const optionFor = (optionValue: any) =>
    options.find((option) => getOptionValue(option) === optionValue);
  const selected = multiple
    ? (value ?? []).map(optionFor).filter((option: any) => option !== undefined)
    : (optionFor(value) ?? null);

  return (
    <SearchableSelect
      multiple={multiple}
      disableCloseOnSelect={multiple}
      autoHighlight
      limitTags={limitTags}
      options={options}
      value={selected}
      getOptionLabel={getOptionLabel}
      getOptionKey={(option: any) => String(getOptionValue(option))}
      isOptionEqualToValue={(option: any, chosen: any) =>
        getOptionValue(option) === getOptionValue(chosen)
      }
      renderOption={(liProps: any, option: any) => {
        const { key, ...rest } = liProps;
        return (
          <li key={key} {...rest} data-value={String(getOptionValue(option))}>
            {renderOptionContent
              ? renderOptionContent(option)
              : getOptionLabel(option)}
          </li>
        );
      }}
      onChange={(_event: any, newValue: any) =>
        onChange(
          multiple
            ? newValue.map(getOptionValue)
            : newValue == null
              ? null
              : getOptionValue(newValue),
        )
      }
      {...props}
    />
  );
};

export default SearchableValueSelect;
