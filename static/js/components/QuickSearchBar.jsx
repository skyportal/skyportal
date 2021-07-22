import React, { useEffect, useState, useRef } from "react";
import { useDispatch } from "react-redux";
import { Link, useHistory } from "react-router-dom";
import { makeStyles } from "@material-ui/core/styles";

import TextField from "@material-ui/core/TextField";
import Autocomplete from "@material-ui/lab/Autocomplete";
import SearchIcon from "@material-ui/icons/Search";
import InputAdornment from "@material-ui/core/InputAdornment";
import CircularProgress from "@material-ui/core/CircularProgress";

import { GET } from "../API";

const useStyles = makeStyles((theme) => ({
  root: {
    "& .MuiOutlinedInput-root": {
      "& fieldset": {
        borderColor: theme.palette.info.main,
      },
      "&:hover fieldset": {
        borderColor: theme.palette.info.main,
      },
      "&.Mui-focused fieldset": {
        borderColor: theme.palette.info.main,
      },
    },
  },
  textField: {
    color: theme.palette.info.main,
  },
  icon: {
    color: theme.palette.info.main,
  },
  paper: {
    backgroundColor: "#fff",
  },
  // These rules help keep the progress wheel centered. Taken from the first example: https://material-ui.com/components/progress/
  progress: {
    display: "flex",
    // The below color rule is not for the progress container, but for CircularProgress. This component only accepts 'primary', 'secondary', or 'inherit'.
    color: theme.palette.info.main,
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
          `/api/sources?sourceID=${val}&pageNumber=1&totalMatches=25&includeComments=false&removeNested=true`,
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
      color="primary"
      id="quick-search-bar"
      style={{ padding: "0.3rem" }}
      classes={{ root: classes.root, paper: classes.paper }}
      getOptionSelected={(option, val) => option.name === val.name}
      getOptionLabel={(option) => option}
      onInputChange={(e, val) => setInputValue(val)}
      onChange={(event, newValue, reason) => {
        setValue(newValue);
        if (reason === "select-option") {
          history.push(`/source/${newValue}`);
        }
        if (reason === "clear") {
          setOpen(false);
        }
      }}
      onClose={() => setOpen(false)}
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
          <Link to={v} id={`quickSearchLinkTo${option}`}>
            {option}
          </Link>
        );
      }}
      renderInput={(params) => (
        <TextField
          // eslint-disable-next-line react/jsx-props-no-spreading
          {...params}
          variant="outlined"
          placeholder="Source"
          fullWidth
          InputProps={{
            ...params.InputProps,
            className: classes.textField,
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" className={classes.icon} />
              </InputAdornment>
            ),
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
  );
};

export default QuickSearchBar;
