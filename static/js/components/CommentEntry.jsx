import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useSelector } from "react-redux";
import { useForm, Controller } from "react-hook-form";
import Checkbox from "@material-ui/core/Checkbox";
import TextField from "@material-ui/core/TextField";
import FormControlLabel from "@material-ui/core/FormControlLabel";
import Typography from "@material-ui/core/Typography";
import Button from "@material-ui/core/Button";
import Box from "@material-ui/core/Box";

import FormValidationError from "./FormValidationError";
import styles from "./CommentEntry.css";

const CommentEntry = ({ addComment }) => {
  const userGroups = useSelector((state) => state.groups.user);

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
      group_ids: Array(userGroups.length).fill(true),
    });
  }, [reset, userGroups]);

  const [groupSelectVisible, setGroupSelectVisible] = useState(false);
  const toggleGroupSelectVisible = () => {
    setGroupSelectVisible(!groupSelectVisible);
  };

  const onSubmit = (data) => {
    const groupIDs = userGroups.map((g) => g.id);
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
        <Box component="div" display={groupSelectVisible ? "block" : "none"}>
          {userGroups.map((userGroup, idx) => (
            <FormControlLabel
              key={userGroup.id}
              control={
                <Controller
                  as={Checkbox}
                  name={`group_ids[${idx}]`}
                  control={control}
                  rules={{ validate: validateGroups }}
                  defaultValue
                />
              }
              label={userGroup.name}
            />
          ))}
        </Box>
      </div>
      <div className={styles.inputDiv}>
        <input type="submit" value="↵" name="submitCommentButton" />
      </div>
    </form>
  );
};

CommentEntry.propTypes = {
  addComment: PropTypes.func.isRequired,
};

export default CommentEntry;
