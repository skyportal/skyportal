import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useDispatch } from "react-redux";
import EditIcon from "@mui/icons-material/Edit";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import makeStyles from "@mui/styles/makeStyles";
import SaveIcon from "@mui/icons-material/Save";
import TextField from "@mui/material/TextField";

import { showNotification } from "baselayer/components/Notifications";
import Button from "./Button";
import * as usersActions from "../ducks/users";

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

const UpdateUserParameter = ({ user, parameter }) => {
  const classes = useStyles();
  const dispatch = useDispatch();

  const [param, setParam] = useState(user[parameter]);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    setParam(user[parameter]);
  }, [user]);

  const handleChange = (e) => {
    setParam(e.target.value);
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    const newState = {};
    newState[parameter] = param;
    const result = await dispatch(usersActions.patchUser(user.id, newState));
    setIsSubmitting(false);
    if (result.status === "success") {
      dispatch(showNotification("Username successfully updated."));
      setDialogOpen(false);
    }
  };

  return (
    <>
      <EditIcon
        data-testid="updateUsernameIconButton"
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
        <DialogTitle>Update Username</DialogTitle>
        <DialogContent>
          <div>
            <TextField
              data-testid="updateUserParameterTextfield"
              size="small"
              label="param"
              value={param}
              name="param"
              onChange={handleChange}
              variant="outlined"
            />
          </div>
          <div className={classes.saveButton}>
            <Button
              secondary
              onClick={() => {
                handleSubmit();
              }}
              endIcon={<SaveIcon />}
              size="large"
              data-testid="updateUserParameterSubmitButton"
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

UpdateUserParameter.propTypes = {
  user: PropTypes.shape({
    id: PropTypes.number,
    username: PropTypes.string,
  }).isRequired,
  parameter: PropTypes.string.isRequired,
};

export default UpdateUserParameter;
