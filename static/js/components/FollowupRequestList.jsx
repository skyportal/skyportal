import React from 'react';
import PropTypes from 'prop-types';
import { useDispatch } from 'react-redux';

import EditFollowupRequestDialog from './EditFollowupRequestDialog';
import * as Actions from '../ducks/source';
import styles from './FollowupRequestList.css';

const FollowupRequestList = ({ followupRequests, instrumentList, instrumentObsParams }) => {
  const dispatch = useDispatch();
  const deleteRequest = (id) => {
    dispatch(Actions.deleteFollowupRequest(id));
  };

  return (
    <div>
      <table className={styles.followupRequestTable}>
        <thead>
          <tr>
            <th>
              Requester
            </th>
            <th>
              Instrument
            </th>
            <th>
              Start Date
            </th>
            <th>
              End Date
            </th>
            <th>
              Priority
            </th>
            <th>
              Status
            </th>
            <th>
              Edit/Delete
            </th>
          </tr>
        </thead>
        <tbody>
          {
            followupRequests.map((followupRequest) => (
              <tr key={followupRequest.id}>
                <td>
                  {followupRequest.requester.username}
                </td>
                <td>
                  {followupRequest.instrument.name}
                </td>
                <td>
                  {followupRequest.start_date.split("T")[0]}
                </td>
                <td>
                  {followupRequest.end_date.split("T")[0]}
                </td>
                <td>
                  {followupRequest.priority}
                </td>
                <td>
                  {followupRequest.status}
                </td>
                <td>
                  {
                    followupRequest.editable &&
                      (
                        <span>
                          <EditFollowupRequestDialog
                            followupRequest={followupRequest}
                            instrumentList={instrumentList}
                            instrumentObsParams={instrumentObsParams}
                          />
                          <button type="button" onClick={() => { deleteRequest(followupRequest.id); }}>
                            Delete
                          </button>
                        </span>
                      )
                  }
                </td>
              </tr>
            ))
          }
        </tbody>
      </table>
    </div>
  );
};

FollowupRequestList.propTypes = {
  followupRequests: PropTypes.arrayOf(PropTypes.shape({
    requester: PropTypes.object,
    instrument: PropTypes.object,
    start_date: PropTypes.string,
    end_date: PropTypes.string,
    priority: PropTypes.string,
    status: PropTypes.string
  })).isRequired,
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

export default FollowupRequestList;
