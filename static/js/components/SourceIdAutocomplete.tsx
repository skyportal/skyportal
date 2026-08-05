import { useEffect, useRef, useState } from "react";

import Autocomplete from "@mui/material/Autocomplete";
import TextField from "@mui/material/TextField";

import { useAppDispatch } from "../types/hooks";
import { GET } from "../API";

// Debounce a changing value so we don't hit the source search on every keypress.
const useDebounced = (value: string, delay: number) => {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const handle = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(handle);
  }, [value, delay]);
  return debounced;
};

// Multi-select of object IDs backed by the same source-name search the top-bar
// QuickSearch uses (`/api/sources?sourceID=...`). Options and value are plain id
// strings (so freeSolo pasted/typed IDs work cleanly); the dropdown shows the
// friendlier "id (TNS name)" label via renderOption.
const SourceIdAutocomplete = ({
  value,
  onChange,
  label = "Object IDs",
  sx,
}: {
  value: string[];
  onChange: (ids: string[]) => void;
  label?: string;
  sx?: object;
}) => {
  const dispatch = useAppDispatch();
  const [options, setOptions] = useState<string[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [loading, setLoading] = useState(false);
  const debounced = useDebounced(inputValue, 400);
  const labels = useRef<Record<string, string>>({});
  const cache = useRef<Record<string, string[]>>({});

  useEffect(() => {
    let active = true;
    if (!debounced) {
      setOptions([]);
      return undefined;
    }
    if (cache.current[debounced]) {
      setOptions(cache.current[debounced]);
      return undefined;
    }
    (async () => {
      setLoading(true);
      const resp: any = await dispatch(
        GET(
          `/api/sources?sourceID=${encodeURIComponent(
            debounced,
          )}&pageNumber=1&numPerPage=25&totalMatches=25&includeComments=false&removeNested=true`,
          "skyportal/FETCH_SOURCE_ID_AUTOCOMPLETE",
        ),
      );
      if (!active) return;
      const ids: string[] = [];
      (resp?.data?.sources ?? []).forEach((s: any) => {
        ids.push(s.id);
        labels.current[s.id] = s.tns_name ? `${s.id} (${s.tns_name})` : s.id;
      });
      cache.current[debounced] = ids;
      setOptions(ids);
      setLoading(false);
    })();
    return () => {
      active = false;
    };
  }, [debounced, dispatch]);

  return (
    <Autocomplete
      multiple
      freeSolo
      size="small"
      sx={sx}
      options={options}
      loading={loading}
      value={value}
      inputValue={inputValue}
      onInputChange={(_e, v) => setInputValue(v)}
      // Server already filters by the query; show everything it returned.
      filterOptions={(opts) => opts}
      filterSelectedOptions
      getOptionLabel={(o) => o}
      renderOption={(props, o) => (
        <li {...props} key={o}>
          {labels.current[o] ?? o}
        </li>
      )}
      onChange={(_e, vals) => {
        // Split any freeSolo entry (e.g. a pasted "a, b c") into separate IDs.
        const ids = (vals as string[])
          .flatMap((v) => v.split(/[\s,]+/))
          .map((s) => s.trim())
          .filter(Boolean);
        onChange(Array.from(new Set(ids)));
        setInputValue("");
      }}
      renderInput={(params) => (
        <TextField
          {...params}
          label={label}
          placeholder="Type to search sources…"
        />
      )}
    />
  );
};

export default SourceIdAutocomplete;
