import React, { useState } from "react";
import PropTypes from "prop-types";
import { useForm, Controller } from "react-hook-form";
import Dialog from "@material-ui/core/Dialog";
import DialogContent from "@material-ui/core/DialogContent";
import DialogTitle from "@material-ui/core/DialogTitle";
import Button from "@material-ui/core/Button";
import Autocomplete from '@material-ui/lab/Autocomplete';
import TextField from '@material-ui/core/TextField';
import FormValidationError from './FormValidationError';


const SharingDialog = ({ title, existingGroups, allGroups, action }) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);

  const { handleSubmit, errors, reset, control } = useForm();

  const groups = allGroups.filter((g) => !existingGroups.includes(g));

  const handleClickOpenDialog = () => {
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
  };

  const onSubmit = async (data) => {
    setIsSubmitting(true);
    const groupIDs = groups.map((g) => g.id);
    const selectedGroupIDs = groupIDs.filter((ID, idx) => data.group_ids[idx]);
    const newCombinedGroupIDs = selectedGroupIDs.concat(existingGroups.map((g) => g.id));
    const result = await action({ group_ids: newCombinedGroupIDs });
    if (result.status === "success") {
      reset();
      setDialogOpen(false);
    } else if (result.status === "error") {
      setIsSubmitting(false);
    }
  };

  return (
    <div>
      <Button onClick={handleClickOpenDialog} name={`shareButton${title}`} variant="contained">
        Share
      </Button>

      <Dialog open={dialogOpen} onClose={handleCloseDialog} style={{ position: "fixed" }}>
        <DialogTitle>
          {title}
        </DialogTitle>
        <DialogContent>
          <form onSubmit={handleSubmit(onSubmit)}>
            {
              errors.group_ids &&
                <FormValidationError message="Select at least one group/user." />
            }
            <Controller
              name="contentTypes"
              as={(
                <Autocomplete
                  multiple
                  name="groupIDs"
                  options={groups}
                  getOptionLabel={(group) => group.name}
                  filterSelectedOptions
                  renderInput={(params) => (
                    <TextField
                      // eslint-disable-next-line react/jsx-props-no-spreading
                      {...params}
                      error={!!errors.groupIDs}
                      helperText="At least one selection is required"
                      variant="outlined"
                      label="Select Additional Groups/Users"
                      placeholder="Select Additional Groups/Users"
                    />
                  )}
                />
               )}
              control={control}
              onChange={([, data]) => data}
              rules={{ validate: (d) => d.length > 0 }}
            />
            <div style={{ textAlign: "center" }}>
              <Button
                variant="contained"
                type="submit"
                name="submitShareButton"
                disabled={isSubmitting}
              >
                Share
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

SharingDialog.propTypes = {
  title: PropTypes.string.isRequired,
  allGroups: PropTypes.arrayOf(PropTypes.shape({
    id: PropTypes.integer,
    name: PropTypes.string
  })).isRequired,
  existingGroups: PropTypes.arrayOf(PropTypes.shape({
    id: PropTypes.integer,
    name: PropTypes.string
  })).isRequired,
  action: PropTypes.func.isRequired
};

export default SharingDialog;
