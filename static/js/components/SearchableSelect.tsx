import { useMemo } from "react";
import Autocomplete, {
  AutocompleteProps,
  createFilterOptions,
} from "@mui/material/Autocomplete";
import CircularProgress from "@mui/material/CircularProgress";
import TextField, { TextFieldProps } from "@mui/material/TextField";

// Token-wise match, so "j smith" finds "J. Smith", with a spaceless fallback
// so "ztfbts" still finds "ZTF BTS".
const makeDefaultFilter = (labelFor: (option: any) => string) => {
  const byToken = createFilterOptions<any>({ stringify: labelFor });
  const spaceless = createFilterOptions<any>({
    stringify: (option: any) => labelFor(option).replace(/\s+/g, ""),
  });
  return (options: any[], state: any) => {
    const tokens = state.inputValue.split(/\s+/).filter(Boolean);
    if (tokens.length === 0) {
      return options;
    }
    const matched = tokens.reduce(
      (remaining: any[], token: string) =>
        byToken(remaining, { ...state, inputValue: token }),
      options,
    );
    return matched.length > 0
      ? matched
      : spaceless(options, { ...state, inputValue: tokens.join("") });
  };
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
