import React from 'react';
import PropTypes from 'prop-types';
import { useSelector, useDispatch } from 'react-redux';
import * as Actions from '../ducks/source';
import * as UserActions from '../ducks/users';
import styles from './AssignmentList.css';
import Link from '@material-ui/core/Link';


function renderAssignment(assignment, deleteAssignment, dispatch, users, observingRunList,
  instrumentList) {
  const { requester_id } = assignment;
  const requester = users[requester_id];

  if (!requester) {
    dispatch(UserActions.fetchUser(requester_id));
  }

  const { run_id } = assignment;
  const run = observingRunList.filter((r) => r.id === run_id)[0];

  const instrument_id = run?.instrument_id;
  const instrument = instrumentList.filter((i) => i.id === instrument_id)[0];
  const load = "Loading...";

  return (
      <tr key={assignment.id}>
        <td>
          <a href={`/run/${assignment.run_id}`}>
            {assignment.run_id}
          </a>
        </td>
        <td>
          {requester?.username || load}
        </td>
        <td>
          {instrument?.name || load}
        </td>
        <td>
          {run?.calendar_date || load}
        </td>
        <td>
          {run?.pi || load}
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
  );
}

const AssignmentList = ({ assignments }) => {
  const dispatch = useDispatch();

  const deleteAssignment = (id) => {
    dispatch(Actions.deleteAssignment(id));
  };

  const { users } = useSelector((state) => state);
  const { observingRunList } = useSelector((state) => state.observingRuns);
  const { instrumentList } = useSelector((state) => state.instruments);

  if (assignments.length === 0) {
    return (
      <b>
        No assignments to show for this object...
      </b>
    );
  }

  if (observingRunList.length === 0) {
    return (
      <b>
        Loading observing run list...
      </b>
    );
  }

  const observingRunDict = {};
  observingRunList.forEach(
    (run) => {
      observingRunDict[run.id] = run;
    }
  );

  assignments.sort((a, b) => {
    return observingRunDict[a.run_id].ephemeris.sunrise_unix - observingRunDict[b.run_id].ephemeris.sunrise_unix;
  });

  return (
    <div>
      <table className={styles.assignmentTable}>
        <thead>
          <tr>
            <th>
              Run Id
            </th>
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
              Delete
            </th>
          </tr>
        </thead>
        <tbody>
          {
            assignments.map(
              (assignment) => renderAssignment(
                assignment, deleteAssignment, dispatch, users, observingRunList, instrumentList
              )
            )
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
