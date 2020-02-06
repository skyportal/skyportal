import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { useSelector, useDispatch } from 'react-redux';
import Button from '@material-ui/core/Button';
import TextField from '@material-ui/core/TextField';
import Dialog from '@material-ui/core/Dialog';
import DialogActions from '@material-ui/core/DialogActions';
import DialogContent from '@material-ui/core/DialogContent';
import DialogContentText from '@material-ui/core/DialogContentText';
import DialogTitle from '@material-ui/core/DialogTitle';
import SettingsIcon from '@material-ui/icons/Settings';


const WidgetPrefsDialog = (props) => {
  const dispatch = useDispatch();
  const [open, setOpen] = useState(false);
  const [state, updateState] = useState({ ...props.formValues });

  useEffect(() => {
    updateState(props.formValues);
  }, [props.formValues]);

  const handleClickOpen = () => {
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
  };

  const handleInputChange = (event) => {
    let stateCopy = { ...state };
    stateCopy[event.target.name] = event.target.value;
    updateState(stateCopy);
  };

  const handleSubmit = () => {
    let payload = {};
    payload[props.stateBranchName] = state;
    dispatch(props.onSubmit(payload));
    setOpen(false);
  };

  return (
    <div>
      <SettingsIcon fontSize="small" onClick={handleClickOpen} />
      <Dialog open={open} onClose={handleClose} style={{ position: "fixed" }}>
        <DialogTitle>
          {props.title}
        </DialogTitle>
        <DialogContent>
          {
            Object.keys(props.formValues).map((key, idx) =>
              <div key={idx}>
                {key}
                :&nbsp;
                <input
                  type="text"
                  size="5"
                  name={key}
                  value={state[key]}
                  onChange={handleInputChange}
                />
              </div>)
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
  formValues: PropTypes.object.isRequired,
  stateBranchName: PropTypes.string.isRequired,
  onSubmit: PropTypes.func.isRequired,
  title: PropTypes.string.isRequired
};

export default WidgetPrefsDialog;
