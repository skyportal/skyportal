import React from 'react';
import PropTypes from 'prop-types';


const FollowupRequestList = ({ followupRequests }) => (
  <div>
    <table>
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
                Edit/Delete buttons
              </td>
            </tr>
          ))
        }
      </tbody>
    </table>
  </div>
);

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
