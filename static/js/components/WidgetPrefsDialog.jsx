import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import { useDispatch } from "react-redux";
import Dialog from "@material-ui/core/Dialog";
import DialogContent from "@material-ui/core/DialogContent";
import DialogTitle from "@material-ui/core/DialogTitle";
import SettingsIcon from "@material-ui/icons/Settings";
import Button from "@material-ui/core/Button";
import { makeStyles } from "@material-ui/core/styles";
import SaveIcon from "@material-ui/icons/Save";
import TextField from "@material-ui/core/TextField";

const useStyles = makeStyles(() => ({
  saveButton: {
    textAlign: "center",
    margin: "1rem",
  },
}));

const WidgetPrefsDialog = ({
  title,
  formValues,
  onSubmit,
  stateBranchName,
}) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const [open, setOpen] = useState(false);
  const [state, updateState] = useState({ ...formValues });

  useEffect(() => {
    updateState(formValues);
  }, [formValues]);

  const handleClickOpen = () => {
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
  };

  const handleInputChange = (event) => {
    const stateCopy = { ...state };
    stateCopy[event.target.id] = event.target.value;
    updateState(stateCopy);
  };

  const handleSubmit = () => {
    const payload = {};
    payload[stateBranchName] = state;
    dispatch(onSubmit(payload));
    setOpen(false);
  };

  return (
    <div>
      <SettingsIcon
        id={`${stateBranchName}SettingsIcon`}
        fontSize="small"
        onClick={handleClickOpen}
      />
      <Dialog open={open} onClose={handleClose} style={{ position: "fixed" }}>
        <DialogTitle>{title}</DialogTitle>
        <DialogContent>
          <form noValidate autoComplete="off">
            {Object.keys(formValues).map((key) => (
              <div key={key}>
                <TextField
                  id={`${key}`}
                  size="small"
                  label={key}
                  value={state[key]}
                  onChange={handleInputChange}
                  variant="outlined"
                />
              </div>
            ))}
          </form>
          <div className={classes.saveButton}>
            <Button
              color="primary"
              onClick={handleSubmit}
              startIcon={<SaveIcon />}
              size="large"
            >
              Save
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

WidgetPrefsDialog.propTypes = {
  formValues: PropTypes.objectOf(PropTypes.string).isRequired,
  stateBranchName: PropTypes.string.isRequired,
  onSubmit: PropTypes.func.isRequired,
  title: PropTypes.string.isRequired,
};

export default WidgetPrefsDialog;
