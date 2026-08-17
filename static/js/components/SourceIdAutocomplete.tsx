import { useCallback, useRef } from "react";

import { useAppDispatch } from "../types/hooks";
import { GET } from "../API";
import SearchableSelect from "./SearchableSelect";

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
  const labels = useRef<Record<string, string>>({});
  const cache = useRef<Record<string, string[]>>({});

  const loadOptions = useCallback(
    async (query: string) => {
      if (cache.current[query]) {
        return cache.current[query];
      }
      const resp: any = await dispatch(
        GET(
          `/api/sources?sourceID=${encodeURIComponent(
            query,
          )}&pageNumber=1&numPerPage=25&totalMatches=25&includeComments=false&removeNested=true`,
          "skyportal/FETCH_SOURCE_ID_AUTOCOMPLETE",
        ),
      );
      const ids: string[] = [];
      (resp?.data?.sources ?? []).forEach((s: any) => {
        ids.push(s.id);
        labels.current[s.id] = s.tns_name ? `${s.id} (${s.tns_name})` : s.id;
      });
      cache.current[query] = ids;
      return ids;
    },
    [dispatch],
  );

  return (
    <SearchableSelect
      multiple
      freeSolo
      label={label}
      sx={sx}
      value={value}
      loadOptions={loadOptions}
      debounceMs={400}
      filterSelectedOptions
      getOptionLabel={(o: any) => o}
      renderOption={(props: any, o: any) => (
        <li {...props} key={o}>
          {labels.current[o] ?? o}
        </li>
      )}
      onChange={(vals: any) => {
        // Split any freeSolo entry (e.g. a pasted "a, b c") into separate IDs.
        const ids = (vals as string[])
          .flatMap((v) => v.split(/[\s,]+/))
          .map((s) => s.trim())
          .filter(Boolean);
        onChange(Array.from(new Set(ids)));
      }}
      placeholder="Type to search sources…"
    />
  );
};

export default SourceIdAutocomplete;
