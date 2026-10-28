import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { makeStyles } from "tss-react/mui";
import { createFilterOptions } from "@mui/material/Autocomplete";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import SearchableSelect from "./SearchableSelect";

import { useAppDispatch } from "../types/hooks";
import { GET } from "../API";
import SaveCandidateGroupsDialog from "./SaveCandidateGroupsDialog";

const SEARCH_TYPES = [
  "Sources",
  "Candidates",
  "Source comments",
  "GCN Events",
  "GCN comments",
  "Users",
] as const;
type SearchType = (typeof SEARCH_TYPES)[number];
const ALLOWED_TYPES = ["All", ...SEARCH_TYPES] as const;
type AllowedType = (typeof ALLOWED_TYPES)[number];

const useStyles = makeStyles()((theme) => ({
  root: {
    "& .MuiOutlinedInput-root": {
      backgroundColor: theme.palette.primary.light,
      borderColor: theme.palette.primary.light,
      borderRadius: "0 1rem 1rem 0",
      "& fieldset": {
        borderColor: theme.palette.primary.light,
      },
      "&:hover fieldset": {
        borderColor: theme.palette.primary.light,
      },
      "&.Mui-focused fieldset": {
        borderColor: theme.palette.primary.light,
      },
    },
    margin: 0,
    padding: 0,
  },
  typeSelect: {
    fontWeight: "bold",
    color: "white",
    backgroundColor: theme.palette.primary.light,
    borderColor: theme.palette.primary.light,
    borderRadius: "1rem 0 0 1rem",
    "& .MuiSelect-icon": {
      color: "white",
    },
    "& fieldset": {
      borderColor: theme.palette.primary.light,
    },
    margin: 0,
    padding: 0,
  },
  textField: {
    fontWeight: "bold",
    color: "white",
  },
}));

function useDebouncer(value: any, delay: number) {
  const [debouncedValue, setDebouncedValue] = useState(value);
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);
    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);
  return debouncedValue;
}

// create a filterOptions for the MUI Autocomplete component
// that ignores cases and spaces when matching
const filterOptions = createFilterOptions<any>({
  matchFrom: "any",
  ignoreCase: true,
  ignoreAccents: true,
  trim: true,
  stringify: (option) => option?.match_name,
});

const QuickSearchBar = () => {
  const { classes } = useStyles();
  const dispatch = useAppDispatch();
  const navigate = useNavigate();

  const [options, setOptions] = useState<any[]>([]);
  const [value, setValue] = useState<any>(null);
  const [inputValue, setInputValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [type, setType] = useState<AllowedType>(ALLOWED_TYPES[0]);
  const [saveDialogObjId, setSaveDialogObjId] = useState<string | null>(null);

  const debouncedInputValue = useDebouncer(inputValue, 500);
  const cache = useRef<Record<string, any>>({});

  useEffect(() => {
    // empty the cache when the type changes
    cache.current = {};
  }, [type]);

  useEffect(() => {
    const get = (searchType: SearchType, val: string) => {
      if (searchType === "GCN Events") {
        return dispatch(
          GET(
            `/api/gcn_event?partialdateobs=${encodeURIComponent(val)}&pageNumber=1&numPerPage=25`,
            "skyportal/FETCH_AUTOCOMPLETE_GCN_EVENTS",
          ),
        );
      }
      if (searchType === "Sources") {
        return dispatch(
          GET(
            `/api/sources?sourceID=${encodeURIComponent(val)}&pageNumber=1&numPerPage=25&includeComments=false&removeNested=true`,
            "skyportal/FETCH_AUTOCOMPLETE_SOURCES",
          ),
        );
      }
      if (searchType === "Candidates") {
        return dispatch(
          GET(
            `/api/candidates?objID=${encodeURIComponent(val)}&nameOnly=true&numPerPage=25`,
            "skyportal/FETCH_AUTOCOMPLETE_CANDIDATES",
          ),
        );
      }
      if (searchType === "Source comments") {
        return dispatch(
          GET(
            `/api/sources/comments?text=${encodeURIComponent(val)}&pageNumber=1&numPerPage=25`,
            "skyportal/FETCH_AUTOCOMPLETE_SOURCE_COMMENTS",
          ),
        );
      }
      if (searchType === "GCN comments") {
        return dispatch(
          GET(
            `/api/gcn_event/comments?text=${encodeURIComponent(val)}&pageNumber=1&numPerPage=25`,
            "skyportal/FETCH_AUTOCOMPLETE_SOURCE_COMMENTS",
          ),
        );
      }
      if (searchType === "Users") {
        return dispatch(
          GET(
            `/api/user?name=${encodeURIComponent(val)}&slim=true&numPerPage=25`,
            "skyportal/FETCH_AUTOCOMPLETE_USERS",
          ),
        );
      }
      return undefined;
    };

    (async (): Promise<any> => {
      if (debouncedInputValue === "") {
        setOptions([]);
        setOpen(false);
        return undefined;
      }

      let newOptions: any[] = [];

      if (cache.current[debouncedInputValue]) {
        setLoading(true);
        newOptions = cache.current[debouncedInputValue];
        setLoading(false);
      } else {
        setLoading(true);
        const searchTypes = type === "All" ? SEARCH_TYPES : [type];
        const responses: any[] = await Promise.all(
          searchTypes.map((searchType) => get(searchType, debouncedInputValue)),
        );
        setLoading(false);

        searchTypes.forEach((searchType, i) => {
          const response = responses[i];
          let matchingEntries: any = [];
          if (searchType === "Sources") {
            matchingEntries = response?.data?.sources;
          } else if (searchType === "Candidates") {
            matchingEntries = response?.data?.candidates;
          } else if (searchType === "GCN Events") {
            matchingEntries = response?.data?.events;
          } else if (["Source comments", "GCN comments"].includes(searchType)) {
            matchingEntries = response?.data;
          } else if (searchType === "Users") {
            matchingEntries = response?.data?.users;
          }

          if (matchingEntries) {
            const rez = Object.keys(matchingEntries).map((key) => {
              if (searchType === "GCN Events") {
                let name = matchingEntries[key].dateobs;
                let match_name = matchingEntries[key].dateobs;
                if ((matchingEntries[key].aliases || []).length > 0) {
                  name = `${name} (${matchingEntries[key].aliases[0]})`;
                  match_name = `${match_name} ${matchingEntries[key].aliases[0]}`;
                }
                return {
                  id: matchingEntries[key].dateobs,
                  name,
                  match_name,
                };
              }
              if (searchType === "Sources") {
                let name = matchingEntries[key].id;
                let match_name = matchingEntries[key].id;
                if (matchingEntries[key]?.tns_name?.length > 0) {
                  name = `${name} (${matchingEntries[key].tns_name})`;
                  match_name = `${match_name} ${
                    matchingEntries[key].tns_name
                  } ${matchingEntries[key].tns_name?.replace(/\s/g, "")}`;
                  // if the tns_name starts with AT, also add to the match_name the name without SN instead of AT
                  // and vice versa. That way if a user searches for an object by AT name but the object
                  // has been classified as SN, the search will still match, and vice versa.
                  if (matchingEntries[key].tns_name.startsWith("AT")) {
                    const sn_name = matchingEntries[key].tns_name.replace(
                      "AT",
                      "SN",
                    );
                    match_name = `${match_name} ${sn_name} ${sn_name.replace(
                      /\s/g,
                      "",
                    )}`;
                  } else if (matchingEntries[key].tns_name.startsWith("SN")) {
                    const sn_name = matchingEntries[key].tns_name.replace(
                      "SN",
                      "AT",
                    );
                    match_name = `${match_name} ${sn_name} ${sn_name.replace(
                      /\s/g,
                      "",
                    )}`;
                  }
                }
                return {
                  id: matchingEntries[key].id,
                  name,
                  match_name,
                };
              }
              if (searchType === "Candidates") {
                return {
                  id: matchingEntries[key].id,
                  name: matchingEntries[key].id,
                  match_name: matchingEntries[key].id,
                };
              }
              if (searchType === "Source comments") {
                // comments here have a text field (that we are searching for a match) and an obj_id field
                return {
                  id: matchingEntries[key].obj_id,
                  name: `${matchingEntries[key].obj_id} - ${matchingEntries[key].text}`,
                  match_name: `${matchingEntries[key].obj_id} ${matchingEntries[key].text}`,
                };
              }
              if (searchType === "GCN comments") {
                // comments here have a text field (that we are searching for a match) and an dateobs field
                return {
                  id: matchingEntries[key].dateobs,
                  name: `${matchingEntries[key].dateobs} - ${matchingEntries[key].text}`,
                  match_name: `${matchingEntries[key].dateobs} ${matchingEntries[key].text}`,
                };
              }
              if (searchType === "Users") {
                const { id, username, first_name, last_name } =
                  matchingEntries[key];
                const fullName = [first_name, last_name]
                  .filter(Boolean)
                  .join(" ");
                return {
                  id,
                  name: fullName ? `${fullName} (${username})` : username,
                  match_name: `${username} ${fullName}`,
                };
              }
              // fallback
              return {
                id: matchingEntries[key].id,
                name: matchingEntries[key].id,
                match_name: matchingEntries[key].id,
              };
            });
            newOptions = [
              ...newOptions,
              ...rez.map((option) => ({ ...option, type: searchType })),
            ];
          }
        });
        cache.current[debouncedInputValue] = newOptions;
      }
      setOpen(true);
      setOptions(newOptions);
      return undefined;
    })();
  }, [dispatch, debouncedInputValue]);

  const handleChangeType = (event: any) => {
    setType(event.target.value);
  };

  const goToPage = (id: any, resourceType: string) => {
    if (["Sources", "Source comments", "Candidates"].includes(resourceType)) {
      navigate(`/source/${id}`);
    } else if (["GCN Events", "GCN comments"].includes(resourceType)) {
      navigate(`/gcn_events/${id}`);
    } else if (resourceType === "Users") {
      navigate(`/user/${id}`);
    }
  };

  return (
    <>
      <div
        data-testid="tour-search"
        style={{
          display: "flex",
          flexDirection: "row",
          alignItems: "center",
          width: "100%",
          justifyContent: "flex-end",
        }}
      >
        <Select
          id="type-select"
          value={type}
          onChange={handleChangeType}
          size="small"
          className={classes.typeSelect}
        >
          {ALLOWED_TYPES.map((allowedType) => (
            <MenuItem key={type} value={allowedType}>
              {allowedType}
            </MenuItem>
          ))}
        </Select>
        <SearchableSelect
          id="quick-search-bar"
          classes={{ root: classes.root, paper: (classes as any).paper }}
          getOptionLabel={(option) => option.name || ""}
          filterOptions={filterOptions}
          onInputChange={(_e, val) => setInputValue(val)}
          onChange={(_event, newValue: any, reason) => {
            if (reason === "selectOption") {
              setInputValue("");
              setValue("");
              setOpen(false);
              if (newValue.type === "Candidates") {
                // Candidates: open the save-to-groups dialog (which also links to
                // the source page) instead of navigating straight there.
                setSaveDialogObjId(newValue.id);
              } else {
                goToPage(newValue.id, newValue.type);
              }
            } else if (reason === "clear") {
              setOpen(false);
            } else {
              setValue(newValue);
            }
          }}
          onClose={() => setOpen(false)}
          groupBy={type === "All" ? (option) => option.type : undefined}
          noOptionsText={`No matching ${type === "All" ? "results" : type}.`}
          options={options}
          open={open}
          loading={loading}
          clearOnEscape
          clearOnBlur
          selectOnFocus
          limitTags={15}
          value={value}
          popupIcon={null}
          placeholder="Search"
          textFieldProps={{
            slotProps: {
              input: { className: classes.textField },
            },
          }}
        />
      </div>
      <SaveCandidateGroupsDialog
        objId={saveDialogObjId}
        open={saveDialogObjId !== null}
        onClose={() => setSaveDialogObjId(null)}
      />
    </>
  );
};

export default QuickSearchBar;
