import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { useDispatch } from 'react-redux';
import Dialog from '@material-ui/core/Dialog';
import DialogContent from '@material-ui/core/DialogContent';
import DialogTitle from '@material-ui/core/DialogTitle';
import SettingsIcon from '@material-ui/icons/Settings';


const WidgetPrefsDialog = ({ title, formValues, onSubmit, stateBranchName }) => {
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
    stateCopy[event.target.name] = event.target.value;
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
      <SettingsIcon fontSize="small" onClick={handleClickOpen} />
      <Dialog open={open} onClose={handleClose} style={{ position: "fixed" }}>
        <DialogTitle>
          {title}
        </DialogTitle>
        <DialogContent>
          {
            Object.keys(formValues).map((key) => (
              <div key={key}>
                {key}
                :&nbsp;
                <input
                  type="text"
                  size="5"
                  name={key}
                  value={state[key]}
                  onChange={handleInputChange}
                />
              </div>
            ))
          }
          <br />
          <br />
          <div style={{ textAlign: "center" }}>
            <button type="button" onClick={handleSubmit}>
              Save
            </button>
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
  title: PropTypes.string.isRequired
};

export default WidgetPrefsDialog;
