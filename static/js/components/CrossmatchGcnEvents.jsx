import React, { useState } from "react";
import { useSelector } from "react-redux";
import ButtonGroup from "@mui/material/ButtonGroup";
import makeStyles from "@mui/styles/makeStyles";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import { useForm, Controller } from "react-hook-form";
import Button from "./Button";

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

const Crossmatch = () => {
  const classes = useStyles();
  const gcnEvents = useSelector((state) => state.gcnEvents);

  const [selectedGcnEventId1, setSelectedGcnEventId1] = useState(null);
  const [selectedLocalizationId1, setSelectedLocalizationId1] = useState(null);
  const [selectedGcnEventId2, setSelectedGcnEventId2] = useState(null);
  const [selectedLocalizationId2, setSelectedLocalizationId2] = useState(null);

  const { control, reset, getValues } = useForm();
  const handleClickReset = () => {
    reset(
      {
        gcneventid1: "",
        gcneventid2: "",
      },
      {
        dirty: false,
      }
    );
  };

  const gcnEventsLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  gcnEvents?.events.forEach((gcnEvent) => {
    gcnEventsLookUp[gcnEvent.id] = gcnEvent;
  });

  const gcnEventsSelect = gcnEvents
    ? [
        {
          id: -1,
          dateobs: "Clear Selection",
        },
        ...gcnEvents.events,
      ]
    : [];

  return (
    <form className={classes.root}>
      <div className={classes.gridItem}>
        <h6> 1: </h6>
        <div className={classes.selectItems}>
          <Controller
            render={({ field: { value } }) => (
              <Select
                inputProps={{ MenuProps: { disableScrollLock: true } }}
                labelId="gcnEventSelectLabel1"
                value={value || ""}
                onChange={(event) => {
                  reset({
                    ...getValues(),
                    gcneventid1:
                      event.target.value === -1 ? "" : event.target.value,
                    localizationid1:
                      event.target.value === -1
                        ? ""
                        : gcnEventsLookUp[event.target.value]?.localizations[0]
                            ?.id || "",
                  });
                  setSelectedGcnEventId1(event.target.value);
                  setSelectedLocalizationId1(
                    gcnEventsLookUp[event.target.value]?.localizations[0]?.id
                  );
                }}
                className={classes.select}
              >
                {gcnEventsSelect?.map((gcnEvent) => (
                  <MenuItem
                    value={gcnEvent.id}
                    key={gcnEvent.id}
                    className={classes.selectItem}
                  >
                    {`${gcnEvent.dateobs}`}
                  </MenuItem>
                ))}
              </Select>
            )}
            name="gcneventid1"
            control={control}
            defaultValue=""
          />
          <Controller
            render={({ field: { onChange, value } }) => (
              <Select
                inputProps={{ MenuProps: { disableScrollLock: true } }}
                labelId="localizationSelectLabel1"
                value={value || ""}
                onChange={(event) => {
                  onChange(event.target.value);
                  setSelectedLocalizationId1(event.target.value);
                }}
                className={classes.select}
                disabled={!selectedGcnEventId1}
              >
                {gcnEventsLookUp[selectedGcnEventId1]?.localizations?.map(
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
            )}
            name="localizationid1"
            control={control}
            defaultValue=""
          />
        </div>
      </div>
      <div className={classes.gridItem}>
        <h6> 2: </h6>

        <div className={classes.selectItems}>
          <Controller
            render={({ field: { value } }) => (
              <Select
                inputProps={{ MenuProps: { disableScrollLock: true } }}
                labelId="gcnEventSelectLabel2"
                value={value || ""}
                onChange={(event) => {
                  reset({
                    ...getValues(),
                    gcneventid2:
                      event.target.value === -1 ? "" : event.target.value,
                    localizationid2:
                      event.target.value === -1
                        ? ""
                        : gcnEventsLookUp[event.target.value]?.localizations[0]
                            ?.id || "",
                  });
                  setSelectedGcnEventId2(event.target.value);
                  setSelectedLocalizationId2(
                    gcnEventsLookUp[event.target.value]?.localizations[0]?.id
                  );
                }}
                className={classes.select}
              >
                {gcnEventsSelect?.map((gcnEvent) => (
                  <MenuItem
                    value={gcnEvent.id}
                    key={gcnEvent.id}
                    className={classes.selectItem}
                  >
                    {`${gcnEvent.dateobs}`}
                  </MenuItem>
                ))}
              </Select>
            )}
            name="gcneventid2"
            control={control}
            defaultValue=""
          />
          <Controller
            render={({ field: { onChange, value } }) => (
              <Select
                inputProps={{ MenuProps: { disableScrollLock: true } }}
                labelId="localizationSelectLabel2"
                value={value || ""}
                onChange={(event) => {
                  onChange(event.target.value);
                  setSelectedLocalizationId2(event.target.value);
                }}
                className={classes.select}
                disabled={!selectedGcnEventId2}
              >
                {gcnEventsLookUp[selectedGcnEventId2]?.localizations?.map(
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
            )}
            name="localizationid2"
            control={control}
            defaultValue=""
          />
        </div>
      </div>
      <ButtonGroup
        primary
        aria-label="contained primary button group"
        className={classes.formButtons}
      >
        <Button
          secondary
          type="submit"
          href={`/api/localizationcrossmatch?id1=${selectedLocalizationId1}&id2=${selectedLocalizationId2}`}
          download={`crossmatch-${selectedLocalizationId1}-${selectedLocalizationId2}.fits`}
          data-testid={`crossmatch_${selectedGcnEventId1}`}
        >
          Download Crossmatch
        </Button>
        <Button primary onClick={handleClickReset}>
          Reset
        </Button>
      </ButtonGroup>
    </form>
  );
};

export default Crossmatch;
