import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import { useDispatch } from "react-redux";
import Dialog from "@material-ui/core/Dialog";
import DialogContent from "@material-ui/core/DialogContent";
import DialogTitle from "@material-ui/core/DialogTitle";
import Checkbox from "@material-ui/core/Checkbox";
import Button from "@material-ui/core/Button";
import FormControlLabel from "@material-ui/core/FormControlLabel";
import { useForm, Controller } from "react-hook-form";

import * as sourceActions from "../ducks/source";
import FormValidationError from "./FormValidationError";


const SaveCandidateGroupSelect = ({ candidateID, userGroups }) => {
  const dispatch = useDispatch();
  const [open, setOpen] = useState(false);

  const { handleSubmit, errors, reset, control, getValues } = useForm();

  useEffect(() => {
    reset({
      group_ids: Array(userGroups.length).fill(false)
    });
  }, [reset, userGroups]);

  const handleClickOpen = () => {
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
  };

  const validateGroups = () => {
    const formState = getValues({ nest: true });
    return formState.group_ids.filter((value) => Boolean(value)).length >= 1;
  };

  const onSubmit = async (data) => {
    data.id = candidateID;
    const groupIDs = userGroups.map((g) => g.id);
    const selectedGroupIDs = groupIDs.filter((ID, idx) => data.group_ids[idx]);
    data.group_ids = selectedGroupIDs;
    const result = await dispatch(sourceActions.saveSource(data));
    if (result.status === "success") {
      reset();
      setOpen(false);
    }
  };

  return (
    <div>
      <Button
        variant="contained"
        onClick={handleClickOpen}
        name={`initialSaveCandidateButton${candidateID}`}
      >
        Save as source
      </Button>
      <Dialog open={open} onClose={handleClose} style={{ position: "fixed" }}>
        <DialogTitle>
          Select one or more groups:
        </DialogTitle>
        <DialogContent>
          <form onSubmit={handleSubmit(onSubmit)}>
            {
              errors.group_ids &&
                <FormValidationError message="Select at least one group." />
            }
            {
              userGroups.map((userGroup, idx) => (
                <FormControlLabel
                  key={userGroup.id}
                  control={(
                    <Controller
                      as={Checkbox}
                      name={`group_ids[${idx}]`}
                      control={control}
                      rules={{ validate: validateGroups }}
                      defaultValue={false}
                    />
                  )}
                  label={userGroup.name}
                />
              ))
            }
            <br />
            <div style={{ textAlign: "center" }}>
              <Button
                variant="contained"
                type="submit"
                name={`finalSaveCandidateButton${candidateID}`}
              >
                Save
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};
SaveCandidateGroupSelect.propTypes = {
  candidateID: PropTypes.string.isRequired,
  userGroups: PropTypes.arrayOf(PropTypes.object).isRequired
};

export default SaveCandidateGroupSelect;
