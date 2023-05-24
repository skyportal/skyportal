import React from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import makeStyles from "@mui/styles/makeStyles";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import Autocomplete from "@mui/material/Autocomplete";
import TextField from "@mui/material/TextField";

import * as gcnEventsActions from "../ducks/gcnEvents";

const useStyles = makeStyles(() => ({
  root: {
    display: "flex",
    flexDirection: "column",
    width: "100%",
  },
  gridItem: {
    display: "flex",
    flexDirection: "row",
  },
  formButtons: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "flex-start",
    alignItems: "center",
    gap: "0.5rem",
    width: "100%",
    margin: "0.5rem",
    marginLeft: "1rem",
  },
  select: {
    width: "100%",
    height: "3rem",
  },
  selectItems: {
    marginLeft: "0.5rem",
    display: "flex",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: "0.25rem",
    width: "30rem",
    minWidth: "15rem",
  },
}));

const FindGcnEvents = ({
  selectedGcnEventId,
  setSelectedGcnEventId,
  selectedLocalizationId,
  setSelectedLocalizationId,
}) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const gcnEvents = useSelector((state) => state.gcnEvents);

  const gcnEventsLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  gcnEvents?.events.forEach((gcnEvent) => {
    gcnEventsLookUp[gcnEvent.id] = gcnEvent;
  });

  return (
    <div className={classes.gridItem}>
      <div className={classes.selectItems}>
        <Autocomplete
          id="gcnEventSelectLabel"
          options={gcnEvents?.events}
          value={
            gcnEvents?.events.find(
              (option) => option.id === selectedGcnEventId
            ) || null
          }
          getOptionLabel={(option) => option?.dateobs || ""}
          className={classes.select}
          // eslint-disable-next-line no-shadow
          onInputChange={(event, value) => {
            if (value !== null) {
              dispatch(
                gcnEventsActions.fetchGcnEvents({
                  partialdateobs: value,
                })
              );
            }
          }}
          onChange={(event, newValue) => {
            if (newValue !== null) {
              setSelectedGcnEventId(newValue.id);
              setSelectedLocalizationId(
                gcnEventsLookUp[newValue.id]?.localizations[0]?.id || ""
              );
            } else {
              setSelectedGcnEventId(null);
              setSelectedLocalizationId(null);
            }
          }}
          renderInput={(params) => <TextField {...params} label="GCN Event" />}
        />
        <Select
          inputProps={{ MenuProps: { disableScrollLock: true } }}
          labelId="localizationSelectLabel"
          value={selectedLocalizationId || ""}
          onChange={(event) => {
            setSelectedLocalizationId(event.target.value);
          }}
          className={classes.select}
          disabled={!selectedGcnEventId}
        >
          {gcnEventsLookUp[selectedGcnEventId]?.localizations?.map(
            (localization) => (
              <MenuItem
                value={localization.id}
                key={localization.id}
                className={classes.selectItem}
              >
                {`${localization.localization_name}`}
              </MenuItem>
            )
          )}
        </Select>
      </div>
    </div>
  );
};

FindGcnEvents.propTypes = {
  selectedGcnEventId: PropTypes.number,
  setSelectedGcnEventId: PropTypes.func.isRequired,
  selectedLocalizationId: PropTypes.number,
  setSelectedLocalizationId: PropTypes.func.isRequired,
};

FindGcnEvents.defaultProps = {
  selectedGcnEventId: null,
  selectedLocalizationId: null,
};

export default FindGcnEvents;
