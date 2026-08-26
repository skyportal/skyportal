import { useMemo } from "react";
import Autocomplete, {
  AutocompleteProps,
  createFilterOptions,
} from "@mui/material/Autocomplete";
import CircularProgress from "@mui/material/CircularProgress";
import TextField, { TextFieldProps } from "@mui/material/TextField";

// Stripped on both sides: MUI only trims the input, never its inner spaces.
const makeDefaultFilter = (labelFor: (option: any) => string) => {
  const stripSpaces = (text: string) => text.replace(/\s+/g, "");
  const filter = createFilterOptions<any>({
    matchFrom: "any",
    stringify: (option: any) => stripSpaces(labelFor(option)),
  });
  return (options: any[], state: any) =>
    filter(options, { ...state, inputValue: stripSpaces(state.inputValue) });
};

export type SearchableSelectProps = Omit<
  AutocompleteProps<any, any, any, any>,
  "renderInput"
> & {
  label?: string;
  required?: boolean;
  error?: boolean;
  helperText?: string;
  placeholder?: string;
  textFieldProps?: TextFieldProps & Record<string, any>;
};

const SearchableSelect = ({
  label,
  required,
  error,
  helperText,
  placeholder,
  textFieldProps,
  getOptionLabel,
  filterOptions,
  loading,
  size = "small",
  ...autocompleteProps
}: SearchableSelectProps) => {
  const labelFor = useMemo(
    () =>
      getOptionLabel ??
      ((option: any) =>
        typeof option === "string"
          ? option
          : String(option?.name ?? option ?? "")),
    [getOptionLabel],
  );
  const defaultFilter = useMemo(() => makeDefaultFilter(labelFor), [labelFor]);

  const { slotProps: tfSlotProps, ...tfRest }: TextFieldProps =
    textFieldProps ?? {};

  return (
    <Autocomplete
      size={size}
      loading={loading}
      getOptionLabel={labelFor}
      filterOptions={filterOptions ?? defaultFilter}
      {...autocompleteProps}
      renderInput={(params) => (
        <TextField
          {...params}
          {...tfRest}
          label={label}
          required={required}
          error={error}
          helperText={helperText}
          placeholder={placeholder}
          slotProps={{
            ...params.slotProps,
            ...(tfSlotProps as any),
            input: {
              ...params.slotProps.input,
              ...((tfSlotProps as any)?.input ?? {}),
              endAdornment: (
                <>
                  {loading ? (
                    <CircularProgress color="inherit" size={18} />
                  ) : null}
                  {(params.slotProps.input as any)?.endAdornment}
                </>
              ),
            },
          }}
        />
      )}
    />
  );
};

export default SearchableSelect;
