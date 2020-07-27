import React from 'react';
import { useSelector, useDispatch } from 'react-redux';
import PropTypes from 'prop-types';
import { useForm, Controller } from 'react-hook-form';
import Select from "@material-ui/core/Select";
import InputLabel from "@material-ui/core/InputLabel";
import TextField from '@material-ui/core/TextField';
import Button from '@material-ui/core/Button';
import FormControl from "@material-ui/core/FormControl";
import MenuItem from "@material-ui/core/MenuItem";
import { makeStyles } from "@material-ui/core/styles";
import * as Actions from '../ducks/source';

import 'react-datepicker/dist/react-datepicker-cssmodules.css';

export function observingRunTitle(observingRun, instrumentList, telescopeList, groups) {
  const { instrument_id } = observingRun;
  const instrument = instrumentList.filter((i) => i.id === instrument_id)[0];
  const instundef = instrument === undefined;

  const telescope_id = !instundef ? instrument.telescope_id : undefined;
  const telescope = !instundef ? telescopeList.filter((t) => t.id === telescope_id)[0] : undefined;
  const telundef = telescope === undefined;

  const usegroup = !!observingRun.group_id && !!groups;
  const group = usegroup ? groups.filter((g) => g.id === observingRun.group_id)[0] : undefined;
  const groupundef = group === undefined;

  return `${observingRun.calendar_date} ${telundef ? "Loading..." : telescope.nickname}/${instundef ? "Loading..." : instrument.name} \
    (PI: ${observingRun.pi}${!groupundef ? `/${group.name})` : ")"}`;
}


function makeMenuItem(observingRun, instrumentList, telescopeList, groups) {
  const render_string = observingRunTitle(observingRun, instrumentList, telescopeList, groups);
  return (
    <MenuItem value={observingRun.id} key={observingRun.id.toString()}>
      {render_string}
    </MenuItem>
  );
}


const AssignmentForm = ({ obj_id, observingRunList }) => {
  const dispatch = useDispatch();
  const instrumentList = useSelector((state) => state.instruments.instrumentList);
  const telescopeList = useSelector((state) => state.telescopes.telescopeList);
  const groups = useSelector((state) => state.groups.all);

  const upcomingRuns = observingRunList.filter((observingrun) => (
    observingrun.sunrise_utc >= Date.now().toISOString()
  ));

  const { handleSubmit, getValues, reset, register, control } = useForm();

  const useStyles = makeStyles((theme) => ({
    formControl: {
      margin: theme.spacing(1),
      minWidth: 120
    }
  }));
  const classes = useStyles();

  if (upcomingRuns.length === 0) {
    return (
      <b>
        No upcoming observing runs to assign target to...
      </b>
    );
  }

  const initialFormState = {
    comment: "",
    run_id: upcomingRuns.length > 0 ? upcomingRuns[0].id : null,
    priority: "1",
    obj_id
  };

  const onSubmit = () => {
    const formData = {
      // Need to add obj_id, etc to form data for request
      ...initialFormState,
      ...getValues({ nest: true })
    };
    // We need to include this field in request, but it isn't in form data
    dispatch(Actions.submitAssignment(formData));
    reset(initialFormState);
  };

  return (
    <div>
      <form onSubmit={handleSubmit(onSubmit)}>
        <h3>
          Assign Target to Observing Run
        </h3>
        <div>
          <FormControl className={classes.formControl}>
            <InputLabel id="assignmentSelectLabel">
              Choose Run
            </InputLabel>
            <Controller
              as={Select}
              labelId="assignmentSelectLabel"
              name="run_id"
              control={control}
              rules={{ required: true }}
              defaultValue={upcomingRuns.length > 0 ? upcomingRuns[0].id : null}
            >
              {upcomingRuns.map((observingRun) => makeMenuItem(
                observingRun, instrumentList, telescopeList, groups
              ))}
            </Controller>
          </FormControl>
          <FormControl className={classes.formControl}>
            <InputLabel id="prioritySelectLabel">
              Priority
            </InputLabel>
            <Controller
              as={Select}
              labelId="prioritySelectLabel"
              defaultValue="1"
              name="priority"
              control={control}
              rules={{ required: true }}
            >
              {
                ["1", "2", "3", "4", "5"].map((prio) => (
                  <MenuItem value={prio} key={prio}>
                    {prio}
                  </MenuItem>
                ))
              }
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
          <Button type="submit" name="assignmentSubmitButton" variant="contained">
            Submit
          </Button>
        </div>
      </form>
    </div>
  );
};

AssignmentForm.propTypes = {
  obj_id: PropTypes.string.isRequired,
  observingRunList: PropTypes.arrayOf(PropTypes.shape({
    id: PropTypes.number,
    instrument: PropTypes.object,
    calendar_date: PropTypes.string,
    pi: PropTypes.string,
  })).isRequired
};

export default AssignmentForm;
