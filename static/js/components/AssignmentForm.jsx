import React from "react";
import { useSelector, useDispatch } from "react-redux";
import PropTypes from "prop-types";
import { useForm, Controller } from "react-hook-form";
import Select from "@material-ui/core/Select";
import InputLabel from "@material-ui/core/InputLabel";
import TextField from "@material-ui/core/TextField";
import Button from "@material-ui/core/Button";
import FormControl from "@material-ui/core/FormControl";
import MenuItem from "@material-ui/core/MenuItem";
import { makeStyles } from "@material-ui/core/styles";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import * as Actions from "../ducks/source";

import "react-datepicker/dist/react-datepicker-cssmodules.css";

dayjs.extend(utc);

export function observingRunTitle(
  observingRun,
  instrumentList,
  telescopeList,
  groups
) {
  const { instrument_id } = observingRun;
  const instrument = instrumentList?.filter((i) => i.id === instrument_id)[0];

  const telescope_id = instrument?.telescope_id;
  const telescope = telescopeList?.filter((t) => t.id === telescope_id)[0];

  const group = groups?.filter((g) => g.id === observingRun.group_id)[0];

  if (
    !(
      observingRun?.calendar_date &&
      instrument?.name &&
      telescope?.name &&
      observingRun?.pi &&
      group?.name
    )
  ) {
    return "Loading ...";
  }

  return `${observingRun?.calendar_date} ${instrument?.name}/${telescope?.nickname} (PI: ${observingRun?.pi} / Group: ${group?.name})`;
}

const AssignmentForm = ({ obj_id, observingRunList }) => {
  const dispatch = useDispatch();
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const groups = useSelector((state) => state.groups.all);

  const upcomingRuns = observingRunList.filter(
    (observingrun) => dayjs.utc(observingrun.ephemeris.sunrise_utc) >= dayjs()
  );

  const { handleSubmit, getValues, reset, register, control } = useForm();

  const useStyles = makeStyles((theme) => ({
    formControl: {
      margin: theme.spacing(1),
      minWidth: 120,
    },
  }));
  const classes = useStyles();

  if (upcomingRuns.length === 0) {
    return <b>No upcoming observing runs to assign target to...</b>;
  }

  const initialFormState = {
    comment: "",
    run_id: upcomingRuns.length > 0 ? upcomingRuns[0].id : null,
    priority: "1",
    obj_id,
  };

  const onSubmit = () => {
    const formData = {
      // Need to add obj_id, etc to form data for request
      ...initialFormState,
      ...getValues(),
    };
    dispatch(Actions.submitAssignment(formData));
    reset(initialFormState);
  };

  return (
    <div>
      <form onSubmit={handleSubmit(onSubmit)}>
        <h3>Assign Target to Observing Run</h3>
        <div>
          <FormControl className={classes.formControl}>
            <InputLabel id="assignmentSelectLabel">Choose Run</InputLabel>
            <Controller
              as={Select}
              labelId="assignmentSelectLabel"
              name="run_id"
              control={control}
              rules={{ required: true }}
              defaultValue={upcomingRuns.length > 0 ? upcomingRuns[0].id : null}
            >
              {upcomingRuns.map((observingRun) => (
                <MenuItem
                  value={observingRun.id}
                  key={observingRun.id.toString()}
                >
                  {observingRunTitle(
                    observingRun,
                    instrumentList,
                    telescopeList,
                    groups
                  )}
                </MenuItem>
              ))}
            </Controller>
          </FormControl>
          <FormControl className={classes.formControl}>
            <InputLabel id="prioritySelectLabel">Priority</InputLabel>
            <Controller
              as={Select}
              labelId="prioritySelectLabel"
              defaultValue="1"
              name="priority"
              control={control}
              rules={{ required: true }}
            >
              {["1", "2", "3", "4", "5"].map((prio) => (
                <MenuItem value={prio} key={prio}>
                  {prio}
                </MenuItem>
              ))}
            </Controller>
          </FormControl>
          <TextField
            id="standard-textarea"
            label="Comment"
            variant="outlined"
            multiline
            defaultValue=""
            name="comment"
            inputRef={register}
          />
          <Button
            type="submit"
            name="assignmentSubmitButton"
            variant="contained"
          >
            Submit
          </Button>
        </div>
      </form>
    </div>
  );
};

AssignmentForm.propTypes = {
  obj_id: PropTypes.string.isRequired,
  observingRunList: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number,
      instrument: PropTypes.shape({
        telescope_id: PropTypes.number,
        name: PropTypes.string,
      }),
      calendar_date: PropTypes.string,
      pi: PropTypes.string,
    })
  ).isRequired,
};

export default AssignmentForm;
