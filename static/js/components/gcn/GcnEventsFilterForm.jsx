import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import Paper from "@mui/material/Paper";
import ButtonGroup from "@mui/material/ButtonGroup";
import TextField from "@mui/material/TextField";
import makeStyles from "@mui/styles/makeStyles";
import Typography from "@mui/material/Typography";
import { Controller, useForm } from "react-hook-form";
import Button from "../Button";

import GcnTagsSelect from "./GcnTagsSelect";
import GcnPropertiesSelect from "./GcnPropertiesSelect";
import LocalizationTagsSelect from "../localization/LocalizationTagsSelect";
import LocalizationPropertiesSelect from "../localization/LocalizationPropertiesSelect";

import * as gcnTagsActions from "../../ducks/gcnTags";
import * as gcnPropertiesActions from "../../ducks/gcnProperties";
import * as localizationTagsActions from "../../ducks/localizationTags";
import * as localizationPropertiesActions from "../../ducks/localizationProperties";

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
  divider: {
    margin: "0.5rem 0rem 0.5rem 0rem",
    minWidth: "100%",
    backgroundColor: "rgba(0, 0, 0, 0.24)",
    height: "2px",
  },
}));

const conversions = {
  FAR: {
    backendUnit: "Hz",
    frontendUnit: "Per year",
    BackendToFrontend: (val) => parseFloat(val) * (365.25 * 24 * 60 * 60),
    FrontendToBackend: (val) => parseFloat(val) / (365.25 * 24 * 60 * 60),
  },
};

const comparators = {
  lt: "<",
  le: "<=",
  eq: "=",
  ne: "!=",
  ge: ">",
  gt: ">=",
};

const GcnEventsFilterForm = ({ handleFilterSubmit }) => {
  const classes = useStyles();
  const dispatch = useDispatch();

  let gcnTags = [];
  gcnTags = gcnTags.concat(useSelector((state) => state.gcnTags));
  gcnTags.sort();

  let localizationTags = [];
  localizationTags = gcnTags.concat(
    useSelector((state) => state.localizationTags),
  );
  localizationTags.sort();

  useEffect(() => {
    dispatch(gcnTagsActions.fetchGcnTags());
  }, [dispatch]);

  useEffect(() => {
    dispatch(localizationTagsActions.fetchLocalizationTags());
  }, [dispatch]);

  let gcnProperties = [];
  gcnProperties = gcnProperties.concat(
    useSelector((state) => state.gcnProperties),
  );
  gcnProperties.sort();

  let localizationProperties = [];
  localizationProperties = localizationProperties.concat(
    useSelector((state) => state.localizationProperties),
  );
  localizationProperties.sort();

  const [selectedGcnTags, setSelectedGcnTags] = useState([]);
  const [rejectedGcnTags, setRejectedGcnTags] = useState([]);
  const [selectedGcnProperties, setSelectedGcnProperties] = useState([]);
  const [selectedLocalizationTags, setSelectedLocalizationTags] = useState([]);
  const [rejectedLocalizationTags, setRejectedLocalizationTags] = useState([]);
  const [selectedLocalizationProperties, setSelectedLocalizationProperties] =
    useState([]);

  useEffect(() => {
    dispatch(gcnPropertiesActions.fetchGcnProperties());
  }, [dispatch]);

  useEffect(() => {
    dispatch(localizationPropertiesActions.fetchLocalizationProperties());
  }, [dispatch]);

  const { handleSubmit, register, control, reset } = useForm();

  const handleClickReset = () => {
    reset({
      startDate: "",
      endDate: "",
    });
    setSelectedGcnTags([]);
    setRejectedGcnTags([]);
    setSelectedGcnProperties([]);
    setSelectedLocalizationTags([]);
    setRejectedLocalizationTags([]);
    setSelectedLocalizationProperties([]);
  };

  const handleFilterPreSubmit = (formData) => {
    formData.gcnTagKeep = selectedGcnTags;
    formData.gcnTagRemove = rejectedGcnTags;
    formData.gcnPropertiesFilter = selectedGcnProperties;
    formData.localizationTagKeep = selectedLocalizationTags;
    formData.localizationTagRemove = rejectedLocalizationTags;
    formData.localizationPropertiesFilter = selectedLocalizationProperties;
    handleFilterSubmit(formData);
  };

  return (
    <Paper className={classes.paper} variant="outlined">
      <div>
        <h4> Filter Gcn Events By</h4>
      </div>
      <form
        className={classes.root}
        onSubmit={handleSubmit(handleFilterPreSubmit)}
      >
        <div className={classes.formItemRightColumn}>
          <Typography variant="subtitle2" className={classes.title}>
            Time Detected (UTC)
          </Typography>
          <Controller
            render={({ field: { onChange, value } }) => (
              <TextField
                size="small"
                label="First Detected After"
                name="startDate"
                inputRef={register("startDate")}
                placeholder="2012-08-30T00:00:00"
                onChange={onChange}
                value={value}
              />
            )}
            name="startDate"
            control={control}
          />
          <Controller
            render={({ field: { onChange, value } }) => (
              <TextField
                size="small"
                label="Last Detected Before"
                name="endDate"
                inputRef={register("endDate")}
                placeholder="2012-08-30T00:00:00"
                onChange={onChange}
                value={value}
              />
            )}
            name="endDate"
            control={control}
          />
        </div>
        <div className={classes.divider} />
        <div className={classes.formItemRightColumn}>
          <Typography variant="subtitle2" className={classes.title}>
            GCN Tags to Keep
          </Typography>
          <GcnTagsSelect
            selectedGcnTags={selectedGcnTags}
            setSelectedGcnTags={setSelectedGcnTags}
          />
          <Typography variant="subtitle2" className={classes.title}>
            GCN Tags to Reject
          </Typography>
          <GcnTagsSelect
            selectedGcnTags={rejectedGcnTags}
            setSelectedGcnTags={setRejectedGcnTags}
          />
          <GcnPropertiesSelect
            selectedGcnProperties={selectedGcnProperties}
            setSelectedGcnProperties={setSelectedGcnProperties}
            conversions={conversions}
            comparators={comparators}
          />
        </div>
        <div className={classes.divider} />
        <div className={classes.formItemRightColumn}>
          <Typography variant="subtitle2" className={classes.title}>
            Localization Tags to Keep
          </Typography>
          <LocalizationTagsSelect
            selectedLocalizationTags={selectedLocalizationTags}
            setSelectedLocalizationTags={setSelectedLocalizationTags}
          />
          <Typography variant="subtitle2" className={classes.title}>
            Localization Tags to Reject
          </Typography>
          <LocalizationTagsSelect
            selectedLocalizationTags={rejectedLocalizationTags}
            setSelectedLocalizationTags={setRejectedLocalizationTags}
          />
          <LocalizationPropertiesSelect
            selectedLocalizationProperties={selectedLocalizationProperties}
            setSelectedLocalizationProperties={
              setSelectedLocalizationProperties
            }
          />
        </div>
        <div className={classes.divider} />
        <div className={classes.formButtons}>
          <ButtonGroup
            variant="contained"
            color="primary"
            aria-label="contained primary button group"
          >
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

GcnEventsFilterForm.propTypes = {
  handleFilterSubmit: PropTypes.func.isRequired,
};

export default GcnEventsFilterForm;
