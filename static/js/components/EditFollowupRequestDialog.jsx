import React, { useState } from 'react';
import PropTypes from 'prop-types';
import Dialog from '@material-ui/core/Dialog';
import DialogContent from '@material-ui/core/DialogContent';

import FollowupRequestForm from './FollowupRequestForm';

const EditFollowupRequestDialog = ({ followupRequest, instrumentList, instrumentObsParams }) => {
  const [open, setOpen] = useState(false);

  const handleClickOpen = () => {
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
  };

  return (
    <span key={followupRequest.id}>
      <button type="button" onClick={handleClickOpen}>
        Edit
      </button>
      <Dialog open={open} onClose={handleClose} style={{ position: "fixed" }}>
        <DialogContent>
          <FollowupRequestForm
            obj_id={followupRequest.obj_id}
            action="editExisting"
            followupRequest={followupRequest}
            instrumentList={instrumentList}
            instrumentObsParams={instrumentObsParams}
            title="Edit Follow-up Request"
            afterSubmit={handleClose}
          />
        </DialogContent>
      </Dialog>
    </span>
  );
};

EditFollowupRequestDialog.propTypes = {
  followupRequest: PropTypes.shape({
    requester: PropTypes.object,
    instrument: PropTypes.object,
    start_date: PropTypes.string,
    end_date: PropTypes.string,
    priority: PropTypes.string,
    status: PropTypes.string,
    obj_id: PropTypes.string,
    id: PropTypes.number
  }).isRequired,
  instrumentList: PropTypes.arrayOf(PropTypes.shape({
    band: PropTypes.string,
    created_at: PropTypes.string,
    id: PropTypes.number,
    name: PropTypes.string,
    type: PropTypes.string,
    telescope_id: PropTypes.number
  })).isRequired,
  instrumentObsParams: PropTypes.objectOf(PropTypes.any).isRequired
};

export default EditFollowupRequestDialog;
