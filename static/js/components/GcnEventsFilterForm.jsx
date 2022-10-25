import React, { useEffect } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import Paper from "@mui/material/Paper";
import ButtonGroup from "@mui/material/ButtonGroup";
import TextField from "@mui/material/TextField";
import makeStyles from "@mui/styles/makeStyles";
import Typography from "@mui/material/Typography";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import { useForm, Controller } from "react-hook-form";
import Button from "./Button";

import * as gcnTagsActions from "../ducks/gcnTags";
import * as gcnPropertiesActions from "../ducks/gcnProperties";

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

const GcnEventsFilterForm = ({ handleFilterSubmit }) => {
  const classes = useStyles();
  const dispatch = useDispatch();

  let gcnTags = [];
  gcnTags = gcnTags.concat(useSelector((state) => state.gcnTags));
  gcnTags.sort();

  useEffect(() => {
    dispatch(gcnTagsActions.fetchGcnTags());
  }, [dispatch]);

  let gcnProperties = [];
  gcnProperties = gcnProperties.concat(
    useSelector((state) => state.gcnProperties)
  );
  gcnProperties.sort();

  const comparators = {
    lt: "<",
    le: "<=",
    eq: "=",
    ne: "!=",
    ge: ">",
    gt: ">=",
  };

  useEffect(() => {
    dispatch(gcnPropertiesActions.fetchGcnProperties());
  }, [dispatch]);

  const { handleSubmit, register, control, reset, getValues } = useForm();

  const handleClickReset = () => {
    reset();
  };

  return (
    <Paper className={classes.paper} variant="outlined">
      <div>
        <h4> Filter Gcn Events By</h4>
      </div>
      <form
        className={classes.root}
        onSubmit={handleSubmit(handleFilterSubmit)}
      >
        <div className={classes.formItem}>
          <Typography variant="subtitle2" className={classes.title}>
            Time Detected (UTC)
          </Typography>
          <TextField
            size="small"
            label="First Detected After"
            name="startDate"
            inputRef={register}
            placeholder="2012-08-30T00:00:00"
          />
          <TextField
            size="small"
            label="Last Detected Before"
            name="endDate"
            inputRef={register}
            placeholder="2012-08-30T00:00:00"
          />
        </div>
        <div className={classes.formItemRightColumn}>
          <Typography variant="subtitle2" className={classes.title}>
            GCN Property Filtering
          </Typography>
          <div className={classes.selectItems}>
            <Controller
              render={({ value }) => (
                <Select
                  inputProps={{ MenuProps: { disableScrollLock: true } }}
                  labelId="gcnPropertySelectLabel"
                  value={value || ""}
                  onChange={(event) => {
                    reset({
                      ...getValues(),
                      property:
                        event.target.value === -1 ? "" : event.target.value,
                    });
                  }}
                  className={classes.select}
                >
                  {gcnProperties?.map((gcnProperty) => (
                    <MenuItem
                      value={gcnProperty}
                      key={gcnProperty}
                      className={classes.selectItem}
                    >
                      {`${gcnProperty}`}
                    </MenuItem>
                  ))}
                </Select>
              )}
              name="property"
              control={control}
              defaultValue=""
            />
          </div>
          <div className={classes.selectItems}>
            <Controller
              render={({ value }) => (
                <Select
                  inputProps={{ MenuProps: { disableScrollLock: true } }}
                  labelId="gcnPropertyComparatorSelectLabel"
                  value={value || ""}
                  onChange={(event) => {
                    reset({
                      ...getValues(),
                      propertyComparator:
                        event.target.value === -1 ? "" : event.target.value,
                    });
                  }}
                  className={classes.select}
                >
                  {Object.keys(comparators)?.map((key) => (
                    <MenuItem
                      value={key}
                      key={key}
                      className={classes.selectItem}
                    >
                      {`${comparators[key]}`}
                    </MenuItem>
                  ))}
                </Select>
              )}
              name="propertyComparator"
              control={control}
              defaultValue="="
            />
          </div>
          <TextField
            size="small"
            label="Property Comparator Value"
            name="propertyComparatorValue"
            inputRef={register}
            placeholder="0.0"
          />
        </div>
        <div className={classes.formItemRightColumn}>
          <Typography variant="subtitle2" className={classes.title}>
            GCN Tag to Keep
          </Typography>
          <div className={classes.selectItems}>
            <Controller
              render={({ value }) => (
                <Select
                  inputProps={{ MenuProps: { disableScrollLock: true } }}
                  labelId="gcnTagSelectLabel"
                  value={value || ""}
                  onChange={(event) => {
                    reset({
                      ...getValues(),
                      tagKeep:
                        event.target.value === -1 ? "" : event.target.value,
                    });
                  }}
                  className={classes.select}
                >
                  {gcnTags?.map((gcnTag) => (
                    <MenuItem
                      value={gcnTag}
                      key={gcnTag}
                      className={classes.selectItem}
                    >
                      {`${gcnTag}`}
                    </MenuItem>
                  ))}
                </Select>
              )}
              name="tagKeep"
              control={control}
              defaultValue=""
            />
          </div>
        </div>
        <div className={classes.formItemRightColumn}>
          <Typography variant="subtitle2" className={classes.title}>
            GCN Tag to Filter Out
          </Typography>
          <div className={classes.selectItems}>
            <Controller
              render={({ value }) => (
                <Select
                  inputProps={{ MenuProps: { disableScrollLock: true } }}
                  labelId="gcnTagRemoveLabel"
                  value={value || ""}
                  onChange={(event) => {
                    reset({
                      ...getValues(),
                      tagRemove:
                        event.target.value === -1 ? "" : event.target.value,
                    });
                  }}
                  className={classes.select}
                >
                  {gcnTags?.map((gcnTag) => (
                    <MenuItem
                      value={gcnTag}
                      key={gcnTag}
                      className={classes.selectItem}
                    >
                      {`${gcnTag}`}
                    </MenuItem>
                  ))}
                </Select>
              )}
              name="tagRemove"
              control={control}
              defaultValue=""
            />
          </div>
        </div>
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
