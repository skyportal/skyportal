import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import Paper from "@mui/material/Paper";
import ButtonGroup from "@mui/material/ButtonGroup";
import TextField from "@mui/material/TextField";
import makeStyles from "@mui/styles/makeStyles";
import Typography from "@mui/material/Typography";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import { Controller, useForm } from "react-hook-form";

import Button from "../Button";

import * as gcnEventsActions from "../../ducks/gcnEvents";

const useStyles = makeStyles((theme) => ({
  paperDiv: {
    padding: "1rem",
    height: "100%",
  },
  tableGrid: {
    width: "100%",
  },
  formControl: {
    margin: theme.spacing(1),
    minWidth: 120,
  },
  paper: {
    padding: "1rem",
    marginTop: "1rem",
    maxHeight: "calc(100vh - 5rem)",
    overflow: "scroll",
  },
  root: {
    display: "flex",
    flexWrap: "wrap",
    justifyContent: "space-between",
    "& .MuiTextField-root": {
      margin: theme.spacing(0.2),
      width: "10rem",
    },
  },
  formItem: {
    flex: "1 1 45%",
    margin: "0.5rem",
  },
  formItemRightColumn: {
    flex: "1 1 50%",
    margin: "0.5rem",
  },
  positionField: {
    width: "33%",
    "& > label": {
      fontSize: "0.875rem",
      [theme.breakpoints.up("sm")]: {
        fontSize: "1rem",
      },
    },
  },
  formButtons: {
    width: "100%",
    margin: "0.5rem",
  },
  title: {
    margin: "0.5rem 0rem 0rem 0rem",
  },
  multiSelect: {
    maxWidth: "100%",
    "& > div": {
      whiteSpace: "normal",
    },
  },
  checkboxGroup: {
    display: "flex",
    flexWrap: "wrap",
    width: "100%",
    "& > label": {
      marginRight: "1rem",
    },
  },
  select: {
    width: "40%",
    height: "3rem",
  },
  selectItems: {
    display: "flex",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "left",
    gap: "0.25rem",
  },
  selectItem: {
    whiteSpace: "break-spaces",
  },
}));

const GalaxyTableFilterForm = ({ handleFilterSubmit }) => {
  const classes = useStyles();
  const dispatch = useDispatch();

  const gcnEvents = useSelector((state) => state.gcnEvents);
  const [selectedGcnEventId, setSelectedGcnEventId] = useState(null);

  useEffect(() => {
    if (gcnEvents?.length > 0 || !gcnEvents) {
      dispatch(gcnEventsActions.fetchGcnEvents());
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const { handleSubmit, register, control, reset, getValues } = useForm();

  const handleClickReset = () => {
    reset({
      galaxyName: "",
      position: {
        ra: "",
        dec: "",
        radius: "",
      },
      minRedshift: "",
      maxRedshift: "",
      minDistance: "",
      maxDistance: "",
      localizationDateobs: "",
      localizationName: "",
      localizationid: "",
      gcneventid: "",
    });
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

  const handleFilterPreSubmit = (formData) => {
    if (formData.gcneventid !== "") {
      formData.localizationDateobs =
        gcnEventsLookUp[formData.gcneventid]?.dateobs;
      if (formData.localizationid !== "") {
        formData.localizationName = gcnEventsLookUp[
          formData.gcneventid
        ]?.localizations?.filter(
          (l) => l.id === formData.localizationid,
        )[0]?.localization_name;
        formData.localizationid = "";
      }
      formData.gcneventid = "";
    }
    handleFilterSubmit(formData);
  };

  return (
    <Paper className={classes.paper} variant="outlined">
      <div>
        <h4> Filter Galaxies By</h4>
      </div>
      <form
        className={classes.root}
        onSubmit={handleSubmit(handleFilterPreSubmit)}
      >
        <div className={classes.formItem}>
          <Typography variant="subtitle2" className={classes.title}>
            Galaxy Name
          </Typography>
          <Controller
            render={({ field: { onChange, value } }) => (
              <TextField
                label="Galaxy Name"
                name="galaxyName"
                inputRef={register("galaxyName")}
                onChange={onChange}
                value={value}
              />
            )}
            name="galaxyName"
            control={control}
          />
        </div>
        <div className={classes.formItemRightColumn}>
          <Typography variant="subtitle2" className={classes.title}>
            Position
          </Typography>
          <Controller
            render={({ field: { onChange, value } }) => (
              <TextField
                size="small"
                label="RA (deg)"
                name="position.ra"
                type="number"
                inputProps={{
                  step: 0.001,
                }}
                inputRef={register("position.ra")}
                className={classes.positionField}
                onChange={onChange}
                value={value}
              />
            )}
            name="position.ra"
            control={control}
          />
          <Controller
            render={({ field: { onChange, value } }) => (
              <TextField
                size="small"
                label="Dec (deg)"
                name="position.dec"
                type="number"
                inputProps={{
                  step: 0.001,
                }}
                inputRef={register("position.dec")}
                className={classes.positionField}
                onChange={onChange}
                value={value}
              />
            )}
            name="position.dec"
            control={control}
          />
          <Controller
            render={({ field: { onChange, value } }) => (
              <TextField
                size="small"
                label="Radius (deg)"
                name="position.radius"
                type="number"
                inputProps={{
                  step: 0.001,
                }}
                inputRef={register("position.radius")}
                className={classes.positionField}
                onChange={onChange}
                value={value}
              />
            )}
            name="position.radius"
            control={control}
          />
        </div>
        <div className={classes.formItem}>
          <Typography variant="subtitle2" className={classes.title}>
            Redshift
          </Typography>
          <Controller
            render={({ field: { onChange, value } }) => (
              <TextField
                size="small"
                label="Min"
                name="minRedshift"
                type="number"
                inputProps={{
                  step: 0.001,
                }}
                inputRef={register("minRedshift")}
                onChange={onChange}
                value={value}
              />
            )}
            name="minRedshift"
            control={control}
          />
          <Controller
            render={({ field: { onChange, value } }) => (
              <TextField
                size="small"
                label="Max"
                name="maxRedshift"
                type="number"
                inputProps={{
                  step: 0.001,
                }}
                inputRef={register("maxRedshift")}
                onChange={onChange}
                value={value}
              />
            )}
            name="maxRedshift"
            control={control}
          />
        </div>
        <div className={classes.formItem}>
          <Typography variant="subtitle2" className={classes.title}>
            Distance [Mpc]
          </Typography>
          <Controller
            render={({ field: { onChange, value } }) => (
              <TextField
                size="small"
                label="Min"
                name="minDistance"
                type="number"
                inputProps={{
                  step: 0.1,
                }}
                inputRef={register("minDistance")}
                onChange={onChange}
                value={value}
              />
            )}
            name="minDistance"
            control={control}
          />
          <Controller
            render={({ field: { onChange, value } }) => (
              <TextField
                size="small"
                label="Max"
                name="maxDistance"
                type="number"
                inputProps={{
                  step: 0.1,
                }}
                inputRef={register("maxDistance")}
                onChange={onChange}
                value={value}
              />
            )}
            name="maxDistance"
            control={control}
          />
        </div>
        <div className={classes.formItemRightColumn}>
          <Typography variant="subtitle2" className={classes.title}>
            GCN Event
          </Typography>
          <div className={classes.selectItems}>
            <Controller
              render={({ field: { value } }) => (
                <Select
                  inputProps={{ MenuProps: { disableScrollLock: true } }}
                  labelId="gcnEventSelectLabel"
                  value={value || ""}
                  onChange={(event) => {
                    reset({
                      ...getValues(),
                      gcneventid:
                        event.target.value === -1 ? "" : event.target.value,
                      localizationid:
                        event.target.value === -1
                          ? ""
                          : gcnEventsLookUp[event.target.value]
                              ?.localizations[0]?.id || "",
                    });
                    setSelectedGcnEventId(event.target.value);
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
              name="gcneventid"
              control={control}
              defaultValue=""
            />
            <Controller
              render={({ field: { onChange, value } }) => (
                <Select
                  inputProps={{ MenuProps: { disableScrollLock: true } }}
                  labelId="localizationSelectLabel"
                  value={value || ""}
                  onChange={(event) => {
                    onChange(event.target.value);
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
                    ),
                  )}
                </Select>
              )}
              name="localizationid"
              control={control}
              defaultValue=""
            />
          </div>
        </div>
        <div className={classes.formButtons}>
          <ButtonGroup primary aria-label="contained primary button group">
            <Button primary type="submit">
              Submit
            </Button>
            <Button primary onClick={handleClickReset}>
              Reset
            </Button>
          </ButtonGroup>
        </div>
      </form>
    </Paper>
  );
};

GalaxyTableFilterForm.propTypes = {
  handleFilterSubmit: PropTypes.func.isRequired,
};

export default GalaxyTableFilterForm;
