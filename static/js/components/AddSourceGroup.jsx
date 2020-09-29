import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import { useDispatch } from "react-redux";
import { useForm, Controller } from "react-hook-form";

import Dialog from "@material-ui/core/Dialog";
import DialogContent from "@material-ui/core/DialogContent";
import DialogTitle from "@material-ui/core/DialogTitle";
import Checkbox from "@material-ui/core/Checkbox";
import Button from "@material-ui/core/Button";
import IconButton from "@material-ui/core/IconButton";
import AddCircleIcon from "@material-ui/icons/AddCircle";
import FormControlLabel from "@material-ui/core/FormControlLabel";
import Tooltip from "@material-ui/core/Tooltip";
import { makeStyles } from "@material-ui/core/styles";

import { showNotification } from "baselayer/components/Notifications";
import * as sourceActions from "../ducks/source";
import FormValidationError from "./FormValidationError";

const useStyles = makeStyles(() => ({
  iconButton: {
    display: "inline-block",
  },
}));

const AddSourceGroup = ({ source, userGroups, icon }) => {
  const classes = useStyles();
  const [isSubmitting, setIsSubmitting] = useState(false);
  // Dialog logic:

  const dispatch = useDispatch();
  const [dialogOpen, setDialogOpen] = useState(false);

  const { handleSubmit, errors, reset, control, getValues } = useForm();

  useEffect(() => {
    reset({
      group_ids: userGroups.map(
        (userGroup) => !source.currentGroupIds.includes(userGroup.id)
      ),
    });
  }, [reset, userGroups, source]);

  const unsavedGroups = userGroups.filter(
    (g) => !source.currentGroupIds.includes(g.id)
  );

  const openDialog = () => {
    setDialogOpen(true);
  };

  const closeDialog = () => {
    setDialogOpen(false);
  };

  const validateGroups = () => {
    const formState = getValues({ nest: true });
    return formState.group_ids.filter((value) => Boolean(value)).length >= 1;
  };

  const onSubmit = async (data) => {
    setIsSubmitting(true);
    data.id = source.id;
    const groupIDs = unsavedGroups.map((g) => g.id);
    const selectedGroupIDs = groupIDs.filter((ID, idx) => data.group_ids[idx]);
    data.group_ids = selectedGroupIDs;
    const result = await dispatch(sourceActions.saveSource(data));
    if (result.status === "success") {
      dispatch(showNotification("Source groups updated successfully", "info"));
      reset();
      setDialogOpen(false);
    } else if (result.status === "error") {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      {icon ? (
        <Tooltip title="Add a group to this source">
          <span>
            <IconButton
              aria-label="add-group"
              onClick={openDialog}
              size="small"
              disabled={isSubmitting || unsavedGroups.length === 0}
              className={classes.iconButton}
            >
              <AddCircleIcon />
            </IconButton>
          </span>
        </Tooltip>
      ) : (
        <Button
          variant="contained"
          aria-label="add-group"
          size="small"
          onClick={openDialog}
          disabled={isSubmitting || unsavedGroups.length === 0}
        >
          Add a group
        </Button>
      )}

      <Dialog
        open={dialogOpen}
        onClose={closeDialog}
        style={{ position: "fixed" }}
      >
        <DialogTitle>Select one or more groups to add:</DialogTitle>
        <DialogContent>
          <form onSubmit={handleSubmit(onSubmit)}>
            {errors.group_ids && (
              <FormValidationError message="Select at least one group." />
            )}
            {unsavedGroups.map((userGroup, idx) => (
              <FormControlLabel
                key={userGroup.id}
                control={
                  <Controller
                    as={Checkbox}
                    name={`group_ids[${idx}]`}
                    control={control}
                    rules={{ validate: validateGroups }}
                  />
                }
                label={userGroup.name}
              />
            ))}
            <br />
            <div style={{ textAlign: "center" }}>
              <Button
                variant="contained"
                type="submit"
                name={`addSourceGroupButton_${source.id}`}
              >
                Save
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
};
AddSourceGroup.propTypes = {
  source: PropTypes.shape({
    id: PropTypes.string,
    currentGroupIds: PropTypes.arrayOf(PropTypes.number),
  }).isRequired,
  userGroups: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number,
      name: PropTypes.string,
    })
  ).isRequired,
  icon: PropTypes.bool,
};

AddSourceGroup.defaultProps = {
  icon: false,
};

export default AddSourceGroup;
