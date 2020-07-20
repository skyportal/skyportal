import React from 'react';
import { useDispatch } from 'react-redux';
import PropTypes from 'prop-types';
import { useForm, Controller } from 'react-hook-form';
import Select from "@material-ui/core/Select";
import InputLabel from "@material-ui/core/InputLabel";
import TextField from '@material-ui/core/TextField';
import AssignmentTurnedInIcon from '@material-ui/icons/AssignmentTurnedIn';
import IconButton from '@material-ui/core/IconButton';
import FormControl from "@material-ui/core/FormControl";
import MenuItem from "@material-ui/core/MenuItem";
import { makeStyles } from "@material-ui/core/styles";
import * as Actions from '../ducks/source';

import 'react-datepicker/dist/react-datepicker-cssmodules.css';

const AssignmentForm = ({ obj_id, observingRunList }) => {

  const dispatch = useDispatch();

  const upcomingRuns = observingRunList.filter((observingrun) => (
    observingrun["sunrise_unix"] >= Date.now()
  ));

  if (upcomingRuns.length === 0){
    return (
      <div></div>
    )
  }

  const initialFormState = {
    comment: null,
    run_id: null,
    priority: "1"
  };

  const { handleSubmit, register, getValues, control, errors, reset } = useForm({
    defaultValues: initialFormState
  });

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

  const useStyles = makeStyles((theme) => ({
    formControl: {
      margin: theme.spacing(1),
      minWidth: 120,
    },
    root: {
      '& .MuiTextField-root': {
        margin: theme.spacing(1),
        width: '25ch',
      },
      '& .MuiSelect-root': {
        margin: theme.spacing(1),
        width: '25ch',
      },
    }
  }));
  const classes = useStyles();

  return (
    <div>
      <form onSubmit={handleSubmit(onSubmit)}>
        <h3>
          Assign Target to Observing Run
        </h3>
        <div>
          <FormControl className={classes.formControl}>
            <InputLabel id="assignmentSelectLabel">
              Instrument
            </InputLabel>
            <Controller
              as={(
                <Select labelId="assignmentSelectLabel">
                  {
                    upcomingRuns.map((observingRun) => (
                      <MenuItem value={observingRun.id} key={observingRun.id}>
                        {observingRun.calendar_date} {observingRun.instrument.telescope.nickname}
                        {observingRun.instrument.name} ({observingRun.pi})
                      </MenuItem>
                    ))
                  }
                </Select>
              )}
              name="run_id"
              rules={{ required: true }}
              control={control}
            />
          </FormControl>
          <FormControl className={classes.formControl}>
            <InputLabel id="prioritySelectLabel">
              Priority
            </InputLabel>
            <Controller
              as={(
                <Select labelId="prioritySelectLabel">
                  {
                    ["1", "2", "3", "4", "5"].map((prio) => (
                      <MenuItem value={prio} key={prio}>
                        {prio}
                      </MenuItem>
                    ))
                  }
                </Select>
              )}
              name="priority"
              rules={{ required: true }}
              control={control}
            />
          </FormControl>
          <FormControl>
            <Controller
              as={(
                <TextField
                  id="standard-textarea"
                  label="Comment"
                  variant="outlined"
                  multiline
                />
              )}
              name="comment"
              rules={{ required: true }}
              control={control}
            />
          </FormControl>
          <FormControl>
            <Controller
              as={(
                <IconButton
                  type="submit"
                  name="assignmentSubmitButton"
                  component="span"
                  aria-label="Submit Assignment"
                  variant="contained"
                >
                  <AssignmentTurnedInIcon />
                </IconButton>
              )}
              name="submitButton"
              control={control}
            />
          </FormControl>
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
  }))
};

export default AssignmentForm;
