import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useSelector } from "react-redux";
import { useForm, Controller } from "react-hook-form";
import Checkbox from "@material-ui/core/Checkbox";
import TextField from "@material-ui/core/TextField";
import { makeStyles } from "@material-ui/core/styles";
import FormControlLabel from "@material-ui/core/FormControlLabel";
import Typography from "@material-ui/core/Typography";
import Button from "@material-ui/core/Button";
import Box from "@material-ui/core/Box";

import FormValidationError from "./FormValidationError";

const useStyles = makeStyles(() => ({
  commentEntry: {
    position: "relative",
  },
  inputDiv: {
    padding: "0.3rem",
  },
  customizeGroupsContainer: {
    flexWrap: "wrap",
    width: "25rem",
  },
}));

const CommentEntry = ({ addComment }) => {
  const styles = useStyles();
  const { userAccessible: groups } = useSelector((state) => state.groups);

  const {
    handleSubmit,
    reset,
    register,
    getValues,
    setValue,
    control,
    errors,
  } = useForm();

  // The file input needs to be registered here, not in the input tag below
  useEffect(() => {
    register({ name: "attachment" });
  }, [register]);

  useEffect(() => {
    reset({
      group_ids: Array(groups.length).fill(true),
    });
  }, [reset, groups]);

  const [groupSelectVisible, setGroupSelectVisible] = useState(false);
  const toggleGroupSelectVisible = () => {
    setGroupSelectVisible(!groupSelectVisible);
  };

  const onSubmit = (data) => {
    const groupIDs = groups.map((g) => g.id);
    const selectedGroupIDs = groupIDs.filter((ID, idx) => data.group_ids[idx]);
    data.group_ids = selectedGroupIDs;
    addComment(data);
    reset();
    setGroupSelectVisible(false);
  };

  const handleFileInputChange = (event) => {
    const file = event.target.files[0];
    setValue("attachment", file);
  };

  const validateGroups = () => {
    const formState = getValues({ nest: true });
    return formState.group_ids.filter((value) => Boolean(value)).length >= 1;
  };

  return (
    <form className={styles.commentEntry} onSubmit={handleSubmit(onSubmit)}>
      <Typography variant="h6">Add comment</Typography>
      <div className={styles.inputDiv}>
        <TextField
          label="Comment text"
          inputRef={register({ required: true })}
          name="text"
          error={!!errors.text}
          helperText={errors.text ? "Required" : ""}
        />
      </div>
      <div className={styles.inputDiv}>
        <label>
          Attachment &nbsp;
          <input
            type="file"
            name="attachment"
            onChange={handleFileInputChange}
          />
        </label>
      </div>
      <div className={styles.inputDiv}>
        {errors.group_ids && (
          <FormValidationError message="Select at least one group." />
        )}
        <Button
          onClick={toggleGroupSelectVisible}
          size="small"
          style={{ textTransform: "none" }}
        >
          Customize Group Access
        </Button>
        <Box
          component="div"
          display={groupSelectVisible ? "flex" : "none"}
          className={styles.customizeGroupsContainer}
        >
          {groups.map((userGroup, idx) => (
            <FormControlLabel
              key={userGroup.id}
              control={
                <Controller
                  render={({ onChange, value }) => (
                    <Checkbox
                      onChange={(event) => onChange(event.target.checked)}
                      checked={value}
                      data-testid={`commentGroupCheckBox${userGroup.id}`}
                    />
                  )}
                  name={`group_ids[${idx}]`}
                  defaultValue
                  control={control}
                  rules={{ validate: validateGroups }}
                />
              }
              label={userGroup.name}
            />
          ))}
        </Box>
      </div>
      <div className={styles.inputDiv}>
        <Button
          variant="contained"
          color="primary"
          type="submit"
          name="submitCommentButton"
        >
          Add Comment
        </Button>
      </div>
    </form>
  );
};

CommentEntry.propTypes = {
  addComment: PropTypes.func.isRequired,
};

export default CommentEntry;
