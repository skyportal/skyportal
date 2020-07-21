import React from 'react';
import PropTypes from 'prop-types';
import { useSelector, useDispatch } from 'react-redux';
import * as Actions from '../ducks/source';
import * as UserActions from '../ducks/users';
import styles from './AssignmentList.css';


function renderAssignment(assignment, deleteAssignment, dispatch, users, observingRunList,
  instrumentList) {
  const { requester_id } = assignment;
  const requester = users[requester_id];
  const requndef = requester === undefined;

  if (requndef) {
    dispatch(UserActions.fetchUser(requester_id));
  }

  const { run_id } = assignment;
  const run = observingRunList.filter((r) => r.id === run_id)[0];
  const runundef = run === undefined;

  const instrument_id = !runundef ? run.instrument_id : undefined;
  const instrument = !runundef ? instrumentList.filter((i) => i.id === instrument_id)[0] : undefined;
  const instundef = instrument === undefined;

  return (
    <tr key={assignment.id}>
      <td>
        {requndef ? "Loading..." : requester.username}
      </td>
      <td>
        {instundef ? "Loading..." : instrument.name}
      </td>
      <td>
        {runundef ? "Loading..." : run.calendar_date}
      </td>
      <td>
        {runundef ? "Loading..." : run.pi}
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

  const users = useSelector((state) => state.users);
  const observingRunList = useSelector((state) => state.observingRuns.observingRunList);
  const instrumentList = useSelector((state) => state.instruments.instrumentList);

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
    const arun = observingRunDict[a.run_id];
    const brun = observingRunDict[b.run_id];
    const atime = arun.sunrise_unix;
    const btime = brun.sunrise_unix;
    return atime - btime;
  });

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
