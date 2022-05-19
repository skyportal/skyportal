import React, { useState, useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";

import { makeStyles } from "@material-ui/core/styles";
import Select from "@material-ui/core/Select";
import MenuItem from "@material-ui/core/MenuItem";
import InputLabel from "@material-ui/core/InputLabel";
import FormControl from "@material-ui/core/FormControl";
import Chip from "@material-ui/core/Chip";
import Typography from "@material-ui/core/Typography";
import { Box } from "@material-ui/core";
import { useForm } from "react-hook-form";
import { showNotification } from "baselayer/components/Notifications";
import TextField from "@material-ui/core/TextField";
import Button from "@material-ui/core/Button";
import UserPreferencesHeader from "./UserPreferencesHeader";

import * as profileActions from "../ducks/profile";

const useStyles = makeStyles((theme) => ({
  formControl: {
    minWidth: "12rem",
    paddingRight: theme.spacing(1),
  },
  chips: {
    display: "flex",
    flexWrap: "wrap",
  },
  chip: {
    margin: 2,
  },
}));

const ITEM_HEIGHT = 48;
const ITEM_PADDING_TOP = 8;
const MenuProps = {
  PaperProps: {
    style: {
      maxHeight: ITEM_HEIGHT * 4.5 + ITEM_PADDING_TOP,
      width: 250,
    },
  },
};

let filters = ["Clear filters"];

// if we find a way to get origins from somewhere, we can use that here
const origins = ["Clear origins", "Muphoten", "STDpipe", "None"];

const PhotometryPlottingPreferences = () => {
  const classes = useStyles();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [filtersList, setFiltersList] = useState([]);
  const [originsList, setOriginsList] = useState([]);
  const [customOrigin, setCustomOrigin] = useState("");
  const profile = useSelector((state) => state.profile.preferences);
  const filters_enums = useSelector(
    (state) => state.enum_types.enum_types.ALLOWED_BANDPASSES
  );

  if (filters_enums && filters.length === 1) {
    filters = filters.concat(filters_enums);
  }

  const dispatch = useDispatch();
  const { handleSubmit, register, reset, errors } = useForm();

  useEffect(() => {
    reset({
      photometryPlottingPreferencesName:
        profile.photometryPlottingPreferencesName,
    });
  }, [reset, profile]);

  const handleChangeFilters = (event) => {
    if (event.target.value.includes("Clear filters")) {
      setFiltersList([]);
    } else {
      setFiltersList(event.target.value);
    }
  };

  const handleChangeOrigins = (event) => {
    if (event.target.value.includes("Clear origins")) {
      setOriginsList([]);
    } else {
      setOriginsList(event.target.value);
    }
  };

  const handleClickSubmit = (event) => {
    console.log("handleClickSubmit");
  };

  const onSubmit = async (initialValues) => {
    let formIsValid = true;
    if (initialValues?.photometryPlottingPreferencesName?.length === 0) {
    }
    console.log(
      "initialValues",
      initialValues?.photometryPlottingPreferencesName?.length
    );
    setIsSubmitting(true);
    const prefs = {
      photometryPlotting: {
        Name: initialValues.photometryPlottingPreferencesName,
        Filters: filtersList,
        Origins: originsList,
      },
    };
    const result = await dispatch(
      profileActions.updateUserPhotometryPreferences(prefs)
    );
    if (result.status === "success") {
      dispatch(showNotification("Profile data saved"));
    }
    setIsSubmitting(false);
  };

  const onDelete = (shortcutName) => {
    const shortcuts = profile?.photometryPlottingFilters;
    delete shortcuts[shortcutName];
    const prefs = {
      photometryPlottingFilters: shortcuts,
    };
    dispatch(profileActions.updateUserPreferences(prefs));
  };

  //let photometryData = photometry_to_filters(photometry);

  return (
    <div>
      <UserPreferencesHeader
        variant="h5"
        title="Photometry Plotting Preferences"
      />
      <UserPreferencesHeader title="Select Automatically Visible Photometry" />
      <UserPreferencesHeader title="Photometry Buttons" />
      <form onSubmit={handleSubmit(onSubmit)}>
        <FormControl className={classes.formControl}>
          <InputLabel id="select-photometry-plot-filter-label">
            Filters
          </InputLabel>
          <Select
            labelId="demo-simple-select-helper-label"
            id="demo-simple-select-helper"
            multiple
            value={filtersList || []}
            // value={profile?.photometryPlottingFilters || []}
            label="Select photometry filter"
            onChange={handleChangeFilters}
            renderValue={(selected) => (
              <Box>
                {selected.map((value) => (
                  <Chip key={value} label={value} />
                ))}
              </Box>
            )}
            MenuProps={MenuProps}
          >
            {filters.map((filter) => (
              <MenuItem key={filter} value={filter}>
                <div data-testid={`filter_${filter}`}>{filter}</div>
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <FormControl className={classes.formControl}>
          <InputLabel id="select-photometry-plot-origin-label">
            Origin
          </InputLabel>
          <Select
            labelId="demo-simple-select-helper-label"
            id="demo-simple-select-helper"
            multiple
            value={originsList || []}
            // value={profile?.photometryPlottingOrigins || []}
            label="Select photometry filter"
            onChange={handleChangeOrigins}
            renderValue={(selected) => (
              <Box>
                {selected.map((value) => (
                  <Chip key={value} label={value} />
                ))}
              </Box>
            )}
            MenuProps={MenuProps}
          >
            {origins.map((origin) => (
              <MenuItem key={origin} value={origin}>
                <div data-testid={`origin_${origin}`}>{origin}</div>
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <TextField
          label="Custom Origin"
          inputRef={register({ required: false })}
          name="txtFiled"
          id="shortcutNameInput"
          error={!!errors.shortcutName}
          helperText={errors.shortcutName ? "OH NO" : ""}
          onChange={(event) => {
            setCustomOrigin(event.target.value);
          }}
        />
        <TextField
          label="Name"
          inputRef={register({
            required: true,
            validate: (value) => {
              if (filtersList.length !== 0 && originsList.length !== 0) {
                console.log(
                  "return",
                  !(
                    value in (profile?.photometryPlotting?.Filters || {}) &&
                    !(value in (profile?.photometryPlotting?.Origins || {}))
                  )
                );
                return !(
                  value in (profile?.photometryPlotting?.Filters || {}) &&
                  !(value in (profile?.photometryPlotting?.Origins || {}))
                );
              }
              return null;
            },
          })}
          name="photometryPlottingPreferencesName"
          id="photometryPlottingPreferencesNameInput"
          error={!!errors.photometryPlottingPreferencesName}
          helperText={
            errors.photometryPlottingPreferencesName
              ? "Required/Shortcut with that name already exists"
              : ""
          }
        />
        <Button
          variant="contained"
          type="submit"
          onClick={(event) => handleClickSubmit(event)}
        >
          SUBMIT
        </Button>
      </form>
      {profile.photometryPlottingFilters && (
        <div>
          <Typography>Shortcuts</Typography>
          {profile?.photometryPlottingFilters.map((shortcutName) => (
            <Chip
              key={shortcutName}
              label={shortcutName}
              onDelete={() => onDelete(shortcutName)}
            />
          ))}
        </div>
      )}
      <UserPreferencesHeader title="Data Point Size" />
    </div>
  );
};

export default PhotometryPlottingPreferences;
