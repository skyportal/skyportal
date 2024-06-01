import React, { useEffect, useRef, useState } from "react";
import { useDispatch } from "react-redux";
import { useNavigate } from "react-router-dom";
import makeStyles from "@mui/styles/makeStyles";

import TextField from "@mui/material/TextField";
import Autocomplete from "@mui/material/Autocomplete";
import CircularProgress from "@mui/material/CircularProgress";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";

import { GET } from "../API";

const ALLOWED_TYPES = ["Sources", "GCN Events"];

const useStyles = makeStyles((theme) => ({
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
  progress: {
    display: "flex",
    color: "white",
    "& > * + *": {
      marginLeft: theme.spacing(2),
    },
  },
}));

function useDebouncer(value, delay) {
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

const QuickSearchBar = () => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const navigate = useNavigate();

  const [options, setOptions] = useState([]);
  const [value, setValue] = useState(null);
  const [inputValue, setInputValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [type, setType] = useState(ALLOWED_TYPES[0]);

  const debouncedInputValue = useDebouncer(inputValue, 500);
  const cache = useRef({});

  useEffect(() => {
    // empty the cache when the type changes
    cache.current = {};
  }, [type]);

  useEffect(() => {
    const get = (val) => {
      if (type === "GCN Events") {
        return dispatch(
          GET(
            `/api/gcn_event?partialdateobs=${val}&pageNumber=1&totalMatches=25`,
            "skyportal/FETCH_AUTOCOMPLETE_GCN_EVENTS",
          ),
        );
      }
      return dispatch(
        GET(
          `/api/sources?sourceID=${val}&pageNumber=1&totalMatches=25&includeComments=false&removeNested=true`,
          "skyportal/FETCH_AUTOCOMPLETE_SOURCES",
        ),
      );
    };

    (async () => {
      if (debouncedInputValue === "") {
        setOptions([]);
        setOpen(false);
        return undefined;
      }

      let newOptions = [];

      if (cache.current[debouncedInputValue]) {
        setLoading(true);
        newOptions = cache.current[debouncedInputValue];
        setLoading(false);
      } else {
        setLoading(true);
        const response = await get(debouncedInputValue);
        setLoading(false);

        let matchingEntries = [];
        if (type === "Sources") {
          matchingEntries = await response.data.sources;
        } else if (type === "GCN Events") {
          matchingEntries = await response.data.events;
        }

        if (matchingEntries) {
          const rez = Object.keys(matchingEntries).map((key) => {
            if (type === "GCN Events") {
              let name = matchingEntries[key].dateobs;
              if ((matchingEntries[key].aliases || []).length > 0) {
                name = `${name} (${matchingEntries[key].aliases[0]})`;
              }
              return {
                id: matchingEntries[key].dateobs,
                name,
              };
            }
            if (type === "Sources") {
              let name = matchingEntries[key].id;
              if (matchingEntries[key]?.tns_name?.length > 0) {
                name = `${name} (${matchingEntries[key].tns_name})`;
              }
              return {
                id: matchingEntries[key].id,
                name,
              };
            }
            // fallback
            return {
              id: matchingEntries[key].id,
              name: matchingEntries[key].id,
            };
          });
          newOptions = [...newOptions, ...rez];
        }
        cache.current[debouncedInputValue] = newOptions;
      }
      setOpen(true);
      setOptions(newOptions);
      return undefined;
    })();
  }, [dispatch, debouncedInputValue]);

  const handleChangeType = (event) => {
    setType(event.target.value);
  };

  const goToPage = (id, resourceType) => {
    if (resourceType === "Sources") {
      navigate(`/source/${id}`);
    } else if (resourceType === "GCN Events") {
      navigate(`/gcn_events/${id}`);
    }
  };

  return (
    <div
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
      <Autocomplete
        color="primary"
        id="quick-search-bar"
        classes={{ root: classes.root, paper: classes.paper }}
        isOptionEqualToValue={(option, val) => option.name === val.name}
        getOptionLabel={(option) => option.name || ""}
        onInputChange={(e, val) => setInputValue(val)}
        onChange={(event, newValue, reason) => {
          if (reason === "selectOption") {
            setInputValue("");
            setValue("");
            setOpen(false);
            goToPage(newValue.id, type);
          } else if (reason === "clear") {
            setOpen(false);
          } else {
            setValue(newValue);
          }
        }}
        onClose={() => setOpen(false)}
        size="small"
        noOptionsText={`No matching ${type}.`}
        options={options}
        open={open}
        loading={loading}
        clearOnEscape
        clearOnBlur
        selectOnFocus
        limitTags={15}
        value={value}
        popupIcon={null}
        renderInput={(params) => (
          <TextField
            // eslint-disable-next-line react/jsx-props-no-spreading
            {...params}
            variant="outlined"
            placeholder="Search"
            fullWidth
            InputProps={{
              ...params.InputProps,
              className: classes.textField,
              endAdornment: (
                <div className={classes.progress}>
                  {loading ? (
                    <CircularProgress size={20} color="inherit" />
                  ) : null}
                </div>
              ),
            }}
          />
        )}
      />
    </div>
  );
};

export default QuickSearchBar;
