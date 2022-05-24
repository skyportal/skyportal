import React from "react";
import { useSelector, useDispatch } from "react-redux";

import { makeStyles, useTheme } from "@material-ui/core/styles";
import Select from "@material-ui/core/Select";
import MenuItem from "@material-ui/core/MenuItem";
import InputLabel from "@material-ui/core/InputLabel";
import FormControl from "@material-ui/core/FormControl";
import Chip from "@material-ui/core/Chip";
import Input from "@material-ui/core/Input";
import * as profileActions from "../ducks/profile";
import UserPreferencesHeader from "./UserPreferencesHeader";

const useStyles = makeStyles((theme) => ({
  formControl: {
    marginTop: theme.spacing(1),
    minWidth: "12rem",
  },
  chips: {
    display: "flex",
    flexWrap: "wrap",
  },
  chip: {
    margin: 2,
  },
}));

const getStyles = (telescopeID, telescopeIDs = [], theme) => ({
  fontWeight:
    telescopeIDs.indexOf(telescopeID) === -1
      ? theme.typography.fontWeightRegular
      : theme.typography.fontWeightMedium,
});

const ObservabilityPreferences = () => {
  const classes = useStyles();
  const theme = useTheme();
  const profile = useSelector((state) => state.profile.preferences);
  const { telescopeList } = useSelector((state) => state.telescopes);

  const dispatch = useDispatch();

  const handleChange = (event) => {
    const prefs = {
      observabilityTelescopes:
        // -1 is used for the "Clear selections" option
        event.target.value.includes(-1) ? [] : event.target.value,
    };
    dispatch(profileActions.updateUserPreferences(prefs));
  };

  telescopeList?.sort((a, b) => (a.name < b.name ? -1 : 1));
  const telescopeIDToName = { "-1": "Clear selections" };
  telescopeList?.forEach((telescope) => {
    telescopeIDToName[telescope.id] = telescope.name;
  });

  return (
    <div>
      <UserPreferencesHeader
        title="Observability Preferences"
        popupText={
          "The telescopes to display observability plots for on sources' observability pages. Leave blank to show all telescopes."
        }
      />
      <FormControl className={classes.formControl}>
        <InputLabel id="select-telescopes-label">Telescopes to show</InputLabel>
        <Select
          labelId="select-telescopes-label"
          data-testid="selectTelescopes"
          MenuProps={{ disableScrollLock: true }}
          multiple
          value={profile?.observabilityTelescopes || []}
          onChange={handleChange}
          input={<Input id="selectTelescopes" />}
          renderValue={(selected) => (
            <div className={classes.chips}>
              {selected
                .sort((a, b) =>
                  telescopeIDToName[a] < telescopeIDToName[b] ? -1 : 1
                )
                .map((value) => (
                  <Chip
                    key={value}
                    label={telescopeIDToName[value]}
                    className={classes.chip}
                  />
                ))}
            </div>
          )}
        >
          {[{ id: -1, name: "Clear selections" }]
            .concat(
              telescopeList?.filter((telescope) => telescope.fixed_location)
            )
            .map((telescope) => (
              <MenuItem
                key={telescope.id}
                value={telescope.id}
                style={getStyles(
                  telescope.name,
                  profile?.observabilityTelescopes || [],
                  theme
                )}
              >
                <div data-testid={`telescope_${telescope.id}`}>
                  {telescope.name}
                </div>
              </MenuItem>
            ))}
        </Select>
      </FormControl>
    </div>
  );
};

export default ObservabilityPreferences;
