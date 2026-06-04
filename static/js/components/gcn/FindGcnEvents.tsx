import React, { useEffect } from "react";
import { makeStyles } from "tss-react/mui";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import Autocomplete from "@mui/material/Autocomplete";
import TextField from "@mui/material/TextField";

import { useAppDispatch, useAppSelector } from "../../types/hooks";
import * as gcnEventsActions from "../../ducks/gcnEvents";

const useStyles = makeStyles()(() => ({
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

interface FindGcnEventsProps {
  selectedGcnEventId?: number | null;
  setSelectedGcnEventId: (...args: any[]) => void;
  selectedLocalizationId?: number | null;
  setSelectedLocalizationId: (...args: any[]) => void;
}

const FindGcnEvents = ({
  selectedGcnEventId = null,
  setSelectedGcnEventId,
  selectedLocalizationId = null,
  setSelectedLocalizationId,
}: FindGcnEventsProps) => {
  const { classes } = useStyles();
  const dispatch = useAppDispatch();
  const gcnEvents = useAppSelector((state) => state["gcnEvents"]) as any;

  const [selectedEvent, setSelectedEvent] = React.useState<any>(null);

  useEffect(() => {
    if (!gcnEvents?.events || gcnEvents?.events?.length === 0) {
      dispatch(gcnEventsActions.fetchGcnEvents());
    }
  }, []);

  const gcnEventsLookUp: Record<string, any> = {};

  if (gcnEvents?.events) {
    gcnEvents?.events.forEach((gcnEvent: any) => {
      gcnEventsLookUp[gcnEvent.id] = gcnEvent;
    });
  }

  const gcnEventsList = gcnEvents?.events ? [...gcnEvents?.events] : [];
  if (selectedEvent !== null && selectedEvent !== undefined) {
    gcnEventsList.push(selectedEvent);
    gcnEventsLookUp[selectedEvent?.id] = selectedEvent;
  }

  return (
    <div className={classes.gridItem}>
      <div className={classes.selectItems}>
        <Autocomplete
          id="gcnEventSelectLabel"
          options={gcnEventsList}
          value={
            gcnEventsList.find((option) => option.id === selectedGcnEventId) ||
            null
          }
          getOptionLabel={(option) =>
            `${option?.dateobs} ${
              option?.aliases?.length > 0 ? `(${option?.aliases})` : ""
            }` || ""
          }
          className={classes.select}
          onInputChange={(event, value) => {
            if (event?.type !== "change") {
              return;
            }
            if (
              value !== null &&
              value !== "" &&
              value !== selectedEvent?.dateobs
            ) {
              setSelectedEvent(null);
              setSelectedGcnEventId(null);
              dispatch(
                gcnEventsActions.fetchGcnEvents({
                  partialdateobs: value,
                }),
              );
            }
          }}
          onChange={(_event, newValue: any) => {
            if (newValue !== null) {
              setSelectedGcnEventId(newValue.id);
              setSelectedEvent(newValue);
              setSelectedLocalizationId(
                gcnEventsLookUp[newValue.id]?.localizations[0]?.id || "",
              );
            } else {
              setSelectedGcnEventId(null);
              setSelectedEvent(null);
              setSelectedLocalizationId(null);
            }
          }}
          renderInput={(params) => (
            <TextField {...params} label="Dateobs/Name" />
          )}
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
          {gcnEventsLookUp[selectedGcnEventId as any]?.localizations?.map(
            (localization: any) => (
              <MenuItem
                value={localization.id}
                key={localization.id}
                {...({ className: (classes as any).selectItem } as any)}
              >
                {`${localization.localization_name}`}
              </MenuItem>
            ),
          )}
        </Select>
      </div>
    </div>
  );
};

export default FindGcnEvents;
