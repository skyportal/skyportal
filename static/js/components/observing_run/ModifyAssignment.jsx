import React, { useEffect } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import { Controller, useForm } from "react-hook-form";
import Select from "@mui/material/Select";
import InputLabel from "@mui/material/InputLabel";
import FormControl from "@mui/material/FormControl";
import TextField from "@mui/material/TextField";
import MenuItem from "@mui/material/MenuItem";
import Typography from "@mui/material/Typography";
import makeStyles from "@mui/styles/makeStyles";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";
import * as Actions from "../../ducks/source";

dayjs.extend(utc);

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
  editButton: {
    margin: "0.5rem",
  },
}));

const ModifyAssignment = ({ assignment, onClose }) => {
  const dispatch = useDispatch();
  const classes = useStyles();

  const { handleSubmit, getValues, reset, register, control } = useForm();

  useEffect(() => {
    reset({
      comment: assignment?.comment,
      priority: assignment?.priority,
    });
  }, [assignment]);

  const onSubmit = () => {
    const newValues = getValues();
    const formData = {};
    // if the priority is different and not null, update it
    if (
      newValues.priority !== assignment.priority &&
      newValues.priority !== null
    ) {
      formData.priority = newValues.priority;
    }
    // if the comment is different, update it
    if (newValues.comment !== assignment.comment) {
      formData.comment = newValues.comment;
    }
    dispatch(Actions.editAssignment(formData, assignment.id)).then(
      (response) => {
        if (response.status === "success") {
          showNotification("Assignment updated successfully", "success");
          if (typeof onClose === "function") {
            onClose();
          }
        }
      },
    );
  };

  return (
    <div>
      <form onSubmit={handleSubmit(onSubmit)}>
        <div className={classes.formContainer}>
          <FormControl className={classes.formControl}>
            <InputLabel id="prioritySelectLabel">Priority</InputLabel>
            <Controller
              inputProps={{ MenuProps: { disableScrollLock: true } }}
              labelId="prioritySelect"
              defaultValue="1"
              name="priority"
              control={control}
              rules={{ required: true }}
              render={({ field: { onChange, value } }) => (
                <Select
                  labelId="prioritySelect"
                  onChange={onChange}
                  value={value}
                  size="small"
                >
                  {["1", "2", "3", "4", "5"].map((prio) => (
                    <MenuItem value={prio} key={prio}>
                      {prio}
                    </MenuItem>
                  ))}
                </Select>
              )}
            />
          </FormControl>
          <TextField
            {...register("comment")}
            id="standard-textarea"
            label="Comment"
            variant="outlined"
            multiline
            defaultValue=""
            name="comment"
            data-testid="assignmentCommentInput"
            size="small"
          />
          <Button
            primary
            type="edit"
            name="assignmentEditButton"
            data-testid="assignmentEditButton"
            className={classes.editButton}
          >
            Submit
          </Button>
        </div>
      </form>
    </div>
  );
};

ModifyAssignment.propTypes = {
  assignment: PropTypes.shape({
    id: PropTypes.number,
    comment: PropTypes.string,
    priority: PropTypes.number,
  }).isRequired,
  onClose: PropTypes.func,
};

ModifyAssignment.defaultProps = {
  onClose: null,
};

export default ModifyAssignment;
