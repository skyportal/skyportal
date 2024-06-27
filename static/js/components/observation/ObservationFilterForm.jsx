import React from "react";
import PropTypes from "prop-types";
import { useSelector } from "react-redux";
import Paper from "@mui/material/Paper";
import ButtonGroup from "@mui/material/ButtonGroup";
import TextField from "@mui/material/TextField";
import makeStyles from "@mui/styles/makeStyles";
import Typography from "@mui/material/Typography";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import { Controller, useForm } from "react-hook-form";
import Button from "../Button";

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

const ObservationFilterForm = ({ handleFilterSubmit }) => {
  const classes = useStyles();

  const { instrumentList } = useSelector((state) => state.instruments);
  const sortedInstrumentList = [...instrumentList];
  sortedInstrumentList.sort((i1, i2) => {
    if (i1.name > i2.name) {
      return 1;
    }
    if (i2.name > i1.name) {
      return -1;
    }
    return 0;
  });

  const { handleSubmit, register, control, reset, getValues } = useForm();

  const handleClickReset = () => {
    reset();
  };

  return (
    <Paper className={classes.paper} variant="outlined">
      <div>
        <h4> Filter Observations By</h4>
      </div>
      <form
        className={classes.root}
        onSubmit={handleSubmit(handleFilterSubmit)}
      >
        <div className={classes.formItem}>
          <Typography variant="subtitle2" className={classes.title}>
            Time (UTC)
          </Typography>
          <Controller
            render={({ field: { onChange, value } }) => (
              <TextField
                size="small"
                label="Time After"
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
                label="Time Before"
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
        <div className={classes.formItemRightColumn}>
          <Typography variant="subtitle2" className={classes.title}>
            Instrument
          </Typography>
          <div className={classes.selectItems}>
            <Controller
              render={({ field: { value } }) => (
                <Select
                  inputProps={{ MenuProps: { disableScrollLock: true } }}
                  labelId="instrumentSelectLabel"
                  value={value || ""}
                  onChange={(event) => {
                    reset({
                      ...getValues(),
                      instrumentName:
                        event.target.value === -1 ? "" : event.target.value,
                    });
                  }}
                  className={classes.select}
                >
                  {sortedInstrumentList?.map((instrument) => (
                    <MenuItem
                      value={instrument.name}
                      key={instrument.name}
                      className={classes.selectItem}
                    >
                      {`${instrument.name}`}
                    </MenuItem>
                  ))}
                </Select>
              )}
              name="instrumentName"
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

ObservationFilterForm.propTypes = {
  handleFilterSubmit: PropTypes.func.isRequired,
};

export default ObservationFilterForm;
