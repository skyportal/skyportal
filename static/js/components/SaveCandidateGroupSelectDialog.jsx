import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { useDispatch } from 'react-redux';
import Dialog from '@material-ui/core/Dialog';
import DialogContent from '@material-ui/core/DialogContent';
import DialogTitle from '@material-ui/core/DialogTitle';
import Checkbox from '@material-ui/core/Checkbox';

import * as Actions from '../ducks/candidate';


const SaveCandidateGroupSelect = ({ candidateID, candidateGroups, userGroups }) => {
  const dispatch = useDispatch();
  const [open, setOpen] = useState(false);
  const initialState = {};
  // Set as checked by default those groups that a candidate already belongs to
  const userGroupIDs = userGroups.map((userGroup) => userGroup.id);
  const candidateGroupIDs = candidateGroups.map((candGroup) => candGroup.id);
  userGroupIDs.forEach((userGroupID) => {
    initialState[userGroupID] = candidateGroupIDs.includes(userGroupID);
  });

  const [state, setState] = useState(initialState);

  const handleClickOpen = () => {
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
  };

  const handleInputChange = (event) => {
    const newState = { ...state };
    newState[event.target.name] = event.target.type === 'checkbox' ?
      event.target.checked : event.target.value;
    setState(newState);
  };

  const handleSubmit = () => {
    const payload = { groupIDs: [] };
    Object.keys(state).forEach((key) => {
      if (state[key] === true) {
        payload.groupIDs.push(key);
      }
    });
    dispatch(Actions.saveCandidate(candidateID, payload));
    setOpen(false);
  };

  return (
    <div>
      <button
        type="button"
        id={`saveCandidateButton_${candidateID}`}
        onClick={handleClickOpen}
      >
        Save as source
      </button>
      <Dialog open={open} onClose={handleClose} style={{ position: "fixed" }}>
        <DialogTitle>
          Select one or more groups:
        </DialogTitle>
        <DialogContent>
          {
            userGroups.map((userGroup) => (
              <div key={userGroup.id}>
                <Checkbox
                  name={userGroup.id}
                  checked={state[userGroup.id]}
                  onChange={handleInputChange}
                  type="checkbox"
                  color="default"
                />
                &nbsp;
                {userGroup.name}
              </div>
            ))
          }
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
SaveCandidateGroupSelect.propTypes = {
  candidateID: PropTypes.string.isRequired,
  candidateGroups: PropTypes.arrayOf(PropTypes.object).isRequired,
  userGroups: PropTypes.arrayOf(PropTypes.object).isRequired
};

export default SaveCandidateGroupSelect;
