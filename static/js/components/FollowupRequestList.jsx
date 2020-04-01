import React from 'react';
import PropTypes from 'prop-types';
import { useDispatch } from 'react-redux';

import * as Actions from '../ducks/source';
import styles from './FollowupRequestList.css';


const FollowupRequestList = ({ followupRequests }) => {
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
              Delete
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
                  <button type="button" onClick={() => { deleteRequest(followupRequest.id); }}>
                    Delete
                  </button>
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
  })).isRequired
};

export default FollowupRequestList;
