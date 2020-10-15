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
import EditIcon from "@material-ui/icons/Edit";
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
  editIcon: {
    display: "inline-block",
  },
}));

const EditSourceGroups = ({ source, userGroups, icon }) => {
  const classes = useStyles();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const dispatch = useDispatch();

  const { handleSubmit, errors, reset, control, getValues } = useForm();

  const unsavedGroups = userGroups.filter(
    (g) => !source.currentGroupIds.includes(g.id)
  );
  const savedGroups = userGroups.filter((g) =>
    source.currentGroupIds.includes(g.id)
  );

  useEffect(() => {
    reset({
      inviteGroupIds: Array(
        userGroups.filter((g) => !source.currentGroupIds.includes(g.id)).length
      ).fill(false),
      unsaveGroupIds: Array(
        userGroups.filter((g) => source.currentGroupIds.includes(g.id)).length
      ).fill(false),
    });
  }, [reset, userGroups, source]);

  const openDialog = () => {
    setDialogOpen(true);
  };

  const closeDialog = () => {
    setDialogOpen(false);
  };

  const validateGroups = () => {
    const formState = getValues({ nest: true });
    return (
      (formState.inviteGroupIds?.length &&
        formState.inviteGroupIds.filter((value) => Boolean(value)).length >=
          1) ||
      (formState.unsaveGroupIds?.length &&
        formState.unsaveGroupIds.filter((value) => Boolean(value)).length >= 1)
    );
  };

  const onSubmit = async (data) => {
    setIsSubmitting(true);
    data.objId = source.id;
    const unsavedGroupIds = unsavedGroups.map((g) => g.id);
    const inviteGroupIds = unsavedGroupIds.filter(
      (ID, idx) => data.inviteGroupIds[idx]
    );
    data.inviteGroupIds = inviteGroupIds;
    const savedGroupIds = savedGroups.map((g) => g.id);
    const unsaveGroupIds = savedGroupIds.filter(
      (ID, idx) => data.unsaveGroupIds[idx]
    );
    data.unsaveGroupIds = unsaveGroupIds;
    const result = await dispatch(sourceActions.inviteGroupToSaveSource(data));
    if (result.status === "success") {
      dispatch(showNotification("Source groups updated successfully", "info"));
      reset();
      setIsSubmitting(false);
      setDialogOpen(false);
    } else if (result.status === "error") {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <div className={classes.editIcon}>
        {icon ? (
          <Tooltip title="Edit source groups">
            <span>
              <IconButton
                aria-label="add-group"
                data-testid={`addGroup_${source.id}`}
                onClick={openDialog}
                size="small"
                disabled={isSubmitting}
                className={classes.iconButton}
              >
                <EditIcon />
              </IconButton>
            </span>
          </Tooltip>
        ) : (
          <Button
            variant="contained"
            aria-label="edit-groups"
            data-testid={`editGroups${source.id}`}
            size="small"
            onClick={openDialog}
            disabled={isSubmitting}
          >
            Edit groups
          </Button>
        )}
      </div>

      <Dialog
        open={dialogOpen}
        onClose={closeDialog}
        style={{ position: "fixed" }}
      >
        <DialogTitle>Edit source groups:</DialogTitle>
        <DialogContent>
          <form onSubmit={handleSubmit(onSubmit)}>
            {(errors.inviteGroupIds || errors.unsaveGroupIds) && (
              <FormValidationError message="Select at least one group." />
            )}
            <div>
              Select new group(s) to which to <b>save</b> source:
            </div>
            {unsavedGroups.map((unsavedGroup, idx) => (
              <FormControlLabel
                key={unsavedGroup.id}
                control={
                  <Controller
                    as={Checkbox}
                    name={`inviteGroupIds[${idx}]`}
                    control={control}
                    rules={{ validate: validateGroups }}
                    data-testid={`addGroupSelect_${unsavedGroup.id}`}
                  />
                }
                label={unsavedGroup.name}
              />
            ))}
            <br />
            <div>
              Optionally, select groups from which to <b>unsave</b> source:
            </div>
            {savedGroups.map((savedGroup, idx) => (
              <FormControlLabel
                key={savedGroup.id}
                control={
                  <Controller
                    as={Checkbox}
                    name={`unsaveGroupIds[${idx}]`}
                    control={control}
                    rules={{ validate: validateGroups }}
                    data-testid={`unsaveGroupSelect_${savedGroup.id}`}
                  />
                }
                label={savedGroup.name}
              />
            ))}
            <div style={{ textAlign: "center" }}>
              <Button
                variant="contained"
                type="submit"
                name={`editSourceGroupsButton_${source.id}`}
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
EditSourceGroups.propTypes = {
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

EditSourceGroups.defaultProps = {
  icon: false,
};

export default EditSourceGroups;
