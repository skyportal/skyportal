import React, { useState } from "react";
import { useSelector, useDispatch } from "react-redux";

import { makeStyles, useTheme } from "@material-ui/core/styles";
import Select from "@material-ui/core/Select";
import MenuItem from "@material-ui/core/MenuItem";
import InputLabel from "@material-ui/core/InputLabel";
import FormControl from "@material-ui/core/FormControl";
import Chip from "@material-ui/core/Chip";
import Input from "@material-ui/core/Input";
import Typography from "@material-ui/core/Typography";
import Popover from "@material-ui/core/Popover";
import IconButton from "@material-ui/core/IconButton";
import HelpOutlineIcon from "@material-ui/icons/HelpOutline";

import * as profileActions from "../ducks/profile";

const useStyles = makeStyles((theme) => ({
  header: {
    display: "flex",
    alignItems: "center",
    "& > h6": {
      marginRight: "0.5rem",
    },
  },
  typography: {
    padding: theme.spacing(2),
  },
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

  //   const [telescopeIDs, setTelescopeIDs] = useState([]);
  const [anchorEl, setAnchorEl] = useState(null);
  const handleClick = (event) => {
    setAnchorEl(event.currentTarget);
  };
  const handleClose = () => {
    setAnchorEl(null);
  };
  const open = Boolean(anchorEl);
  const id = open ? "simple-popover" : undefined;

  const handleChange = (event) => {
    const prefs = {
      observabilityTelescopes:
        // -1 is used for the "Clear selections" option
        event.target.value.includes(-1) ? [] : event.target.value,
    };
    dispatch(profileActions.updateUserPreferences(prefs));
  };

  telescopeList.sort((a, b) => (a.name < b.name ? -1 : 1));
  const telescopeIDToName = { "-1": "Clear selections" };
  telescopeList.forEach((telescope) => {
    telescopeIDToName[telescope.id] = telescope.name;
  });

  return (
    <div>
      <div className={classes.header}>
        <Typography variant="h6" display="inline">
          Observability Preferences
        </Typography>
        <IconButton aria-label="help" size="small" onClick={handleClick}>
          <HelpOutlineIcon />
        </IconButton>
      </div>
      <Popover
        id={id}
        open={open}
        anchorEl={anchorEl}
        onClose={handleClose}
        anchorOrigin={{
          vertical: "top",
          horizontal: "right",
        }}
        transformOrigin={{
          vertical: "top",
          horizontal: "left",
        }}
      >
        <Typography className={classes.typography}>
          The telescopes to display observability plots for on sources&apos;
          observability pages. Leave blank to show all telescopes.
        </Typography>
      </Popover>
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
              telescopeList.filter((telescope) => telescope.fixed_location)
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
