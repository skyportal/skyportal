import React from 'react';
import PropTypes from 'prop-types';
import { useDispatch } from 'react-redux';

import EditFollowupRequestDialog from './EditFollowupRequestDialog';
import * as Actions from '../ducks/source';
import styles from './AssignmentList.css';

const AssignmentList = ({ assignments }) => {
  const dispatch = useDispatch();

  const deleteAssignment = (id) => {
    dispatch(Actions.deleteAssignment(id));
  };

  if (assignments.length === 0){
    return <div></div>
  }

  return (
    <div>
      <table className={styles.assignmentTable}>
        <thead>
          <tr>
            <th>
              Requester
            </th>
            <th>
              Instrument
            </th>
            <th>
              Run Date
            </th>
            <th>
              PI
            </th>
            <th>
              Priority
            </th>
            <th>
              Status
            </th>
            <th>
              Comment
            </th>
            <th>
              Edit/Delete
            </th>
          </tr>
        </thead>
        <tbody>
          {
            assignments.map((assignment) => (
              <tr key={assignment.id}>
                <td>
                  {assignment.requester.username}
                </td>
                <td>
                  {assignment.run.instrument.name}
                </td>
                <td>
                  {assignment.run.calendar_date}
                </td>
                <td>
                  {assignment.run.pi}
                </td>
                <td>
                  {assignment.priority}
                </td>
                <td>
                  {assignment.status}
                </td>
                <td>
                  {assignment.comment}
                </td>
                <td>
                  <span>
                    <button type="button" onClick={() => { deleteAssignment(assignment.id); }}>
                      Delete
                    </button>
                  </span>
                </td>
              </tr>
            ))
          }
        </tbody>
      </table>
    </div>
  );
};

AssignmentList.propTypes = {
  assignments: PropTypes.arrayOf(PropTypes.shape({
    id: PropTypes.number,
    requester: PropTypes.object,
    run: PropTypes.object,
    priority: PropTypes.string,
    status: PropTypes.string,
    comment: PropTypes.string
  })).isRequired,
};

export default AssignmentList;
