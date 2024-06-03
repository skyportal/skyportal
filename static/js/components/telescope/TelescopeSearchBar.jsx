import React, { useState } from "react";
import makeStyles from "@mui/styles/makeStyles";
import PropTypes from "prop-types";

import TextField from "@mui/material/TextField";
import Autocomplete from "@mui/material/Autocomplete";
import SearchIcon from "@mui/icons-material/Search";
import InputAdornment from "@mui/material/InputAdornment";
import CircularProgress from "@mui/material/CircularProgress";

import TelescopeInfo from "./TelescopeInfo";

const useStyles = makeStyles((theme) => ({
  root: {
    "& .MuiOutlinedInput-root": {
      "& fieldset": {
        borderColor: "#333333",
      },
      "&:hover fieldset": {
        borderColor: "#333333",
      },
      "&.Mui-focused fieldset": {
        borderColor: "#333333",
      },
    },
  },
  textField: {
    color: "#333333",
  },
  icon: {
    color: "#333333",
  },
  paper: {
    backgroundColor: "#F0F8FF",
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

const TelescopeSearchBar = ({ telescopeList }) => {
  const [inputValue, setInputValue] = useState("");
  const loading = useState(false);
  const [open, setOpen] = useState(false);

  const classes = useStyles();

  let results = [];
  const handleChange = (e) => {
    e.preventDefault();
    setInputValue(e.target.value);
  };
  if (inputValue.length > 0) {
    results = telescopeList.filter((telescope) =>
      telescope.name.toLowerCase().match(inputValue.toLowerCase()),
    );
  }

  return (
    <div>
      <Autocomplete
        color="primary"
        id="telescopes-search-bar"
        style={{ padding: "0.3rem" }}
        classes={{ root: classes.root, paper: classes.paper }}
        isOptionEqualToValue={(option, val) => option.name === val.name}
        getOptionLabel={(option) => option}
        onInputChange={handleChange}
        onClose={() => setOpen(false)}
        size="small"
        noOptionsText="No matching telescopes."
        open={open}
        limitTags={15}
        popupIcon={null}
        options={telescopeList || []}
        renderInput={(params) => (
          <TextField
            // eslint-disable-next-line react/jsx-props-no-spreading
            {...params}
            variant="outlined"
            placeholder="Telescope"
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
      {results.length !== 0 && (
        <TelescopeInfo search searchedTelescopeList={Array.from(results)} />
      )}
    </div>
  );
};

TelescopeSearchBar.propTypes = {
  // eslint-disable-next-line react/forbid-prop-types
  telescopeList: PropTypes.arrayOf(PropTypes.any),
  filter: PropTypes.func,
};

TelescopeSearchBar.defaultProps = {
  telescopeList: [],
  filter: null,
};

export default TelescopeSearchBar;
