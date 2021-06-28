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
import Typography from "@material-ui/core/Typography";
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

  if (!(observingRun?.calendar_date && instrument?.name && telescope?.name)) {
    return "Loading ...";
  }

  let result = `${observingRun?.calendar_date} ${instrument?.name}/${telescope?.nickname}`;

  if (observingRun?.pi || group?.name) {
    result += " (";
    if (observingRun?.pi) {
      result += `PI: ${observingRun.pi}`;
    }
    if (group?.name) {
      result += ` / Group: ${group?.name}`;
    }
    result += ")";
  }

  return result;
}

const AssignmentForm = ({ obj_id, observingRunList }) => {
  const dispatch = useDispatch();
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const groups = useSelector((state) => state.groups.all);

  const { handleSubmit, getValues, reset, register, control } = useForm();

  const useStyles = makeStyles((theme) => ({
    formControl: {
      margin: theme.spacing(1),
      minWidth: 120,
    },
    formContainer: {
      display: "flex",
      flexFlow: "row wrap",
      alignItems: "center",
    },
    observingRunSelectItem: {
      whiteSpace: "break-spaces",
    },
    submitButton: {
      margin: "0.5rem",
    },
  }));
  const classes = useStyles();

  const upcomingObservingRuns = observingRunList.filter((run) =>
    dayjs().isBefore(dayjs(run.run_end_utc))
  );

  if (upcomingObservingRuns.length === 0) {
    return (
      <Typography variant="subtitle2">
        No upcoming observing runs to assign target to...
      </Typography>
    );
  }

  const initialFormState = {
    comment: "",
    run_id:
      upcomingObservingRuns.length > 0 ? upcomingObservingRuns[0].id : null,
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
        <Typography variant="h6">Assign Target to Observing Run</Typography>
        <div className={classes.formContainer}>
          <FormControl className={classes.formControl}>
            <InputLabel id="assignmentSelectLabel">Choose Run</InputLabel>
            <Controller
              as={Select}
              inputProps={{ MenuProps: { disableScrollLock: true } }}
              labelId="assignmentSelectLabel"
              name="run_id"
              data-testid="assignmentSelect"
              control={control}
              rules={{ required: true }}
              defaultValue={
                upcomingObservingRuns.length > 0
                  ? upcomingObservingRuns[0].id
                  : null
              }
            >
              {upcomingObservingRuns.map((observingRun) => (
                <MenuItem
                  value={observingRun.id}
                  key={observingRun.id.toString()}
                  className={classes.observingRunSelectItem}
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
              inputProps={{ MenuProps: { disableScrollLock: true } }}
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
            data-testid="assignmentCommentInput"
            size="small"
            inputRef={register}
          />
          <Button
            type="submit"
            name="assignmentSubmitButton"
            data-testid="assignmentSubmitButton"
            variant="contained"
            color="primary"
            className={classes.submitButton}
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
