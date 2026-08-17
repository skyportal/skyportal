import { useEffect, useMemo, useRef, useState } from "react";
import Autocomplete, { createFilterOptions } from "@mui/material/Autocomplete";
import CircularProgress from "@mui/material/CircularProgress";
import TextField from "@mui/material/TextField";

import { useDebouncedValue } from "../hooks/useDebouncedValue";

// Ignore case and whitespace when matching, so "j smith" finds "J. Smith".
// Must match on the label: an object option would stringify to "[object Object]".
const makeDefaultFilter = (labelFor: (option: any) => string) =>
  createFilterOptions<any>({
    matchFrom: "any",
    stringify: (option: any) => labelFor(option).replace(/\s+/g, ""),
    trim: true,
  });

export interface SearchableSelectProps {
  label: string;
  /** Optional: some call sites drive selection entirely through onChange. */
  value?: any;
  /** `reason` is MUI's change reason ("selectOption", "clear", ...). */
  onChange: (value: any, reason?: string) => void;
  /** Static mode: the full list to filter locally. */
  options?: any[];
  /** Async mode: called with the debounced query; its result becomes the options. */
  loadOptions?: (query: string) => Promise<any[]>;
  multiple?: boolean;
  /** Allow values not present in the list (pasted ids, new tags, ...). */
  freeSolo?: boolean;
  getOptionLabel?: (option: any) => string;
  isOptionEqualToValue?: (option: any, value: any) => boolean;
  renderOption?: (props: any, option: any) => React.ReactNode;
  groupBy?: (option: any) => string;
  renderGroup?: (params: any) => React.ReactNode;
  disableClearable?: boolean;
  blurOnSelect?: boolean;
  clearOnBlur?: boolean;
  /** Override the default case/whitespace-insensitive matcher (static mode). */
  filterOptions?: (options: any[], state: any) => any[];
  limitTags?: number;
  /** Controlled open state; omit to let the component manage it. */
  open?: boolean;
  onOpen?: () => void;
  onClose?: () => void;
  /** Controlled input text; omit to let the component manage it. */
  inputValue?: string;
  noOptionsText?: React.ReactNode;
  /** Show the spinner for a fetch the caller is running itself. */
  loading?: boolean;
  clearOnEscape?: boolean;
  popupIcon?: React.ReactNode;
  filterSelectedOptions?: boolean;
  disableCloseOnSelect?: boolean;
  disabled?: boolean;
  required?: boolean;
  error?: boolean;
  helperText?: string;
  placeholder?: string;
  /** Async mode: wait this long after typing stops before querying. */
  debounceMs?: number;
  /** Async mode: do not query until the input is at least this long. */
  minChars?: number;
  /**
   * Notified on every keystroke, in addition to the component's own tracking.
   * For sites that drive an external query (e.g. a redux fetch) from typing
   * rather than returning options from `loadOptions`.
   */
  onInputChange?: (event: any, value: string, reason: string) => void;
  dataTestId?: string;
  id?: string;
  classes?: Record<string, string>;
  /** Escape hatch for per-site input styling (variant, placeholder, ...). */
  textFieldProps?: Record<string, any>;
  className?: string;
  style?: any;
  sx?: any;
  /** Defaults to "small"; appearance is owned here so pickers look alike. */
  size?: "small" | "medium";
  /** Leave unset: MUI reads the raw prop and defaults it to true. */
  fullWidth?: boolean;
}

/**
 * A searchable select over a list of options.
 *
 * Two modes, chosen by which prop you pass:
 *
 *   options     - the whole list is known up front and is filtered in the browser
 *   loadOptions - the list comes from the server; the query is debounced first
 *
 * Everything else (single/multi, freeSolo, labelling, disabled state) behaves
 * the same in both, so a call site can move from one to the other by swapping
 * that one prop.
 *
 * Appearance is deliberately fixed here -- MUI's default "outlined" variant at
 * size "small" -- so every picker in the app matches. Callers keep `sx` for
 * layout (width, margins), which is their business; `textFieldProps` is the
 * escape hatch for the rare site that genuinely looks different.
 */
const SearchableSelect = ({
  label,
  value,
  onChange,
  options,
  loadOptions,
  multiple = false,
  freeSolo = false,
  getOptionLabel,
  isOptionEqualToValue,
  renderOption,
  groupBy,
  renderGroup,
  disableClearable,
  blurOnSelect,
  clearOnBlur,
  filterOptions,
  limitTags,
  open,
  onOpen,
  onClose,
  inputValue: controlledInputValue,
  noOptionsText,
  loading: controlledLoading,
  clearOnEscape,
  popupIcon,
  filterSelectedOptions,
  disableCloseOnSelect,
  disabled = false,
  required = false,
  error = false,
  helperText,
  placeholder,
  debounceMs = 500,
  minChars = 1,
  onInputChange,
  dataTestId,
  id,
  classes,
  textFieldProps,
  className,
  style,
  sx,
  size = "small",
  fullWidth,
}: SearchableSelectProps) => {
  const isAsync = typeof loadOptions === "function";

  const [internalInputValue, setInternalInputValue] = useState("");
  const inputValue = controlledInputValue ?? internalInputValue;
  const [asyncOptions, setAsyncOptions] = useState<any[]>([]);
  const [asyncLoading, setAsyncLoading] = useState(false);
  const debouncedInput = useDebouncedValue(inputValue, debounceMs);

  // Identifies the in-flight request so a slow earlier response cannot
  // overwrite the options for a query the user has already moved past.
  const requestRef = useRef(0);

  useEffect(() => {
    if (!isAsync) {
      return;
    }
    if (debouncedInput.length < minChars) {
      setAsyncOptions([]);
      setAsyncLoading(false);
      return;
    }

    const requestId = requestRef.current + 1;
    requestRef.current = requestId;
    let cancelled = false;

    setAsyncLoading(true);
    loadOptions!(debouncedInput)
      .then((results) => {
        if (!cancelled && requestRef.current === requestId) {
          setAsyncOptions(results ?? []);
        }
      })
      .catch(() => {
        if (!cancelled && requestRef.current === requestId) {
          setAsyncOptions([]);
        }
      })
      .finally(() => {
        if (!cancelled && requestRef.current === requestId) {
          setAsyncLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [debouncedInput, isAsync, loadOptions, minChars]);

  // slotProps is merged into the input below rather than spread, so a call
  // site can add its own adornments without losing the loading spinner.
  const { slotProps: tfSlotProps, ...tfRest } = textFieldProps ?? {};

  const loading = controlledLoading ?? asyncLoading;

  const resolvedOptions = isAsync ? asyncOptions : (options ?? []);

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

  return (
    <Autocomplete
      id={id}
      classes={classes as any}
      className={className}
      style={style}
      sx={sx}
      size={size}
      fullWidth={fullWidth}
      multiple={multiple}
      freeSolo={freeSolo}
      disabled={disabled}
      value={value}
      onChange={(_event, newValue, reason) => onChange(newValue, reason)}
      inputValue={inputValue}
      onInputChange={(event, newInput, reason) => {
        setInternalInputValue(newInput);
        onInputChange?.(event, newInput, reason);
      }}
      options={resolvedOptions}
      getOptionLabel={labelFor}
      isOptionEqualToValue={isOptionEqualToValue}
      renderOption={renderOption}
      groupBy={groupBy}
      renderGroup={renderGroup}
      disableClearable={disableClearable}
      blurOnSelect={blurOnSelect}
      clearOnBlur={clearOnBlur}
      limitTags={limitTags}
      {...(open !== undefined ? { open } : {})}
      onOpen={onOpen}
      onClose={onClose}
      noOptionsText={noOptionsText}
      clearOnEscape={clearOnEscape}
      popupIcon={popupIcon}
      filterSelectedOptions={filterSelectedOptions}
      disableCloseOnSelect={disableCloseOnSelect}
      loading={loading}
      // In async mode the server has already filtered; re-filtering in the
      // browser would hide results whose match is not a literal substring.
      filterOptions={
        filterOptions ?? (isAsync ? (opts) => opts : defaultFilter)
      }
      data-testid={dataTestId}
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
