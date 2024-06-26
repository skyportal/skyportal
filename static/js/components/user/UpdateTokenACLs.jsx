import React, { useState } from "react";
import PropTypes from "prop-types";
import { useDispatch } from "react-redux";
import EditIcon from "@mui/icons-material/Edit";
import Checkbox from "@mui/material/Checkbox";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import makeStyles from "@mui/styles/makeStyles";
import SaveIcon from "@mui/icons-material/Save";
import FormControlLabel from "@mui/material/FormControlLabel";
import { Controller, useForm } from "react-hook-form";

import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";

import * as ProfileActions from "../../ducks/profile";

const useStyles = makeStyles(() => ({
  saveButton: {
    textAlign: "center",
    margin: "1rem",
  },
  editIcon: {
    height: "0.75rem",
    cursor: "pointer",
  },
}));

const UpdateTokenACLs = ({ tokenId, currentACLs, availableACLs }) => {
  const classes = useStyles();
  const dispatch = useDispatch();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { control, getValues } = useForm();

  const handleSubmit = async () => {
    const { acls } = getValues();
    const selectedACLs = availableACLs?.filter((include, idx) => acls[idx]);
    const data = {};
    data.acls = selectedACLs;

    setIsSubmitting(true);
    const result = await dispatch(ProfileActions.updateToken(tokenId, data));
    setIsSubmitting(false);
    if (result.status === "success") {
      dispatch(showNotification("ACLs successfully updated."));
      setDialogOpen(false);
    }
  };

  return (
    <>
      <EditIcon
        data-testid="updateCoordinatesIconButton"
        fontSize="small"
        className={classes.editIcon}
        onClick={() => {
          setDialogOpen(true);
        }}
      />
      <Dialog
        open={dialogOpen}
        onClose={() => {
          setDialogOpen(false);
        }}
        style={{ position: "fixed" }}
      >
        <DialogTitle>Update ACLs</DialogTitle>
        <DialogContent>
          <div>
            {availableACLs?.map((acl, idx) => (
              <FormControlLabel
                key={acl}
                control={
                  <Controller
                    render={({ field: { onChange, value } }) => (
                      <Checkbox
                        onChange={(event) => onChange(event.target.checked)}
                        checked={value}
                        data-testid={`acls[${idx}]`}
                      />
                    )}
                    name={`acls[${idx}]`}
                    control={control}
                    defaultValue={currentACLs?.includes(acl)}
                  />
                }
                label={acl}
              />
            ))}
          </div>
          <div className={classes.saveButton}>
            <Button
              secondary
              onClick={() => {
                handleSubmit();
              }}
              endIcon={<SaveIcon />}
              size="large"
              data-testid="updateACLsSubmitButton"
              disabled={isSubmitting}
            >
              Save
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

UpdateTokenACLs.propTypes = {
  tokenId: PropTypes.string.isRequired,
  availableACLs: PropTypes.arrayOf(PropTypes.string).isRequired,
  currentACLs: PropTypes.arrayOf(PropTypes.string).isRequired,
};

export default UpdateTokenACLs;
