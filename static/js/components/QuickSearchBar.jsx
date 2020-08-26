import React, { useEffect, useState, useRef } from "react";
import { useDispatch } from "react-redux";
import { useHistory } from "react-router-dom";
import { makeStyles } from "@material-ui/core/styles";

import Link from "@material-ui/core/Link";
import TextField from "@material-ui/core/TextField";
import Autocomplete from "@material-ui/lab/Autocomplete";
import SearchIcon from "@material-ui/icons/Search";
import InputAdornment from "@material-ui/core/InputAdornment";
import CircularProgress from "@material-ui/core/CircularProgress";

import { GET } from "../API";

const useStyles = makeStyles(() => ({
  root: {
    background: "#9394c3",
    "& label": {
      color: "black",
    },
    "& label.Mui-focused": {
      color: "white",
    },
  },
  label: {
    "& label": {
      color: "white",
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
  const dispatch = useDispatch();
  const [options, setOptions] = useState([]);
  const [value, setValue] = useState(null);
  const [inputValue, setInputValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const history = useHistory();

  const classes = useStyles();

  const debouncedInputValue = useDebouncer(inputValue, 500);
  const cache = useRef({});

  useEffect(() => {
    const get = (val) =>
      dispatch(
        GET(
          `/api/sources?sourceID=${val}&pageNumber=1&totalMatches=25`,
          "skyportal/FETCH_AUTOCOMPLETE_SOURCES"
        )
      );
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

        const matchingSources = await response.data.sources;

        if (matchingSources) {
          const rez = Object.keys(matchingSources).map(
            (key) => matchingSources[key].id
          );
          newOptions = [...newOptions, ...rez];
        }
        cache.current[debouncedInputValue] = newOptions;
      }
      setOpen(true);
      setOptions(newOptions);
      return undefined;
    })();
  }, [dispatch, debouncedInputValue]);

  return (
    <Autocomplete
      id="quick-search-bar"
      style={{ width: "100%", padding: "0.5rem" }}
      getOptionSelected={(option, val) => option.name === val.name}
      getOptionLabel={(option) => option}
      onInputChange={(e, val) => {
        if (e.constructor.name === "SyntheticEvent") {
          setInputValue(val);
        }
      }}
      onChange={(event, newValue, reason) => {
        setValue(newValue);
        if (reason === "select-option") {
          history.push(`/source/${newValue}`);
        }
        if (reason === "clear") {
          setOpen(false);
        }
      }}
      onClose={() => {
        setOpen(false);
      }}
      size="small"
      noOptionsText="No matching sources."
      options={options}
      open={open}
      loading={loading}
      clearOnEscape
      clearOnBlur
      selectOnFocus
      limitTags={15}
      value={value}
      popupIcon={null}
      renderOption={(option) => {
        const v = `/source/${option}`;
        return (
          <Link href={v} id={`quickSearchLinkTo${option}`} color="inherit">
            {option}
          </Link>
        );
      }}
      renderInput={(params) => (
        <TextField
          // eslint-disable-next-line react/jsx-props-no-spreading
          {...params}
          className={classes.root}
          variant="outlined"
          placeholder="Source"
          fullWidth
          InputProps={{
            ...params.InputProps,
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" color="inherit" />
              </InputAdornment>
            ),
            endAdornment: (
              <>
                {loading ? (
                  <CircularProgress color="inherit" size={15} />
                ) : null}
                {params.InputProps.endAdornment}
              </>
            ),
          }}
        />
      )}
    />
  );
};

export default QuickSearchBar;
