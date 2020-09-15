import React, { useEffect } from "react";
import PropTypes from "prop-types";
import { useSelector, useDispatch } from "react-redux";
import { makeStyles } from "@material-ui/core/styles";
import IconButton from "@material-ui/core/IconButton";
import DeleteIcon from "@material-ui/icons/Delete";
import * as Actions from "../ducks/source";
import * as UserActions from "../ducks/users";

const useStyles = makeStyles(() => ({
  container: {
    overflowX: "scroll",
    width: "100%",
  },
  assignmentTable: {
    borderSpacing: "0.7em",
  },
  verticalCenter: {
    margin: 0,
    position: "absolute",
    top: "50%",
    msTransform: "translateY(-50%)",
    transform: "translateY(-50%)",
  },
}));

const AssignmentList = ({ assignments }) => {
  const styles = useStyles();
  const dispatch = useDispatch();

  const deleteAssignment = (id) => {
    dispatch(Actions.deleteAssignment(id));
  };

  const { users } = useSelector((state) => state);
  const { observingRunList } = useSelector((state) => state.observingRuns);
  const { instrumentList } = useSelector((state) => state.instruments);

  // fetch all the requester ids before rendering the component
  const requesterIDs = assignments.map((assignment) => assignment.requester_id);
  const uniqueRequesterIDs = [...new Set(requesterIDs)];
  uniqueRequesterIDs.sort((a, b) => a - b);

  // use useEffect to only send 1 fetchUser per User
  useEffect(() => {
    uniqueRequesterIDs.forEach((id) => {
      if (!users[id]) {
        dispatch(UserActions.fetchUser(id));
      }
    });
  }, [...uniqueRequesterIDs, users, dispatch]);

  if (assignments.length === 0) {
    return <b>No assignments to show for this object...</b>;
  }

  if (observingRunList.length === 0) {
    return <b>Loading observing run list...</b>;
  }

  const observingRunDict = {};
  observingRunList.forEach((run) => {
    observingRunDict[run.id] = run;
  });

  assignments.sort(
    (a, b) =>
      observingRunDict[a.run_id].ephemeris.sunrise_unix -
      observingRunDict[b.run_id].ephemeris.sunrise_unix
  );

  return (
    <div className={styles.container}>
      <table className={styles.assignmentTable}>
        <thead>
          <tr>
            <th>Run Id</th>
            <th>Requester</th>
            <th>Instrument</th>
            <th>Run Date</th>
            <th>PI</th>
            <th>Priority</th>
            <th>Status</th>
            <th>Comment</th>
            <th>Delete</th>
          </tr>
        </thead>
        <tbody>
          {assignments.map((assignment) => {
            const { requester_id } = assignment;
            const requester = users[requester_id];

            const { run_id } = assignment;
            const run = observingRunList.filter((r) => r.id === run_id)[0];

            const instrument_id = run?.instrument_id;
            const instrument = instrumentList.filter(
              (i) => i.id === instrument_id
            )[0];
            const load = "Loading...";

            return (
              <tr key={assignment.id}>
                <td>
                  <a href={`/run/${assignment.run_id}`}>{assignment.run_id}</a>
                </td>
                <td>{requester?.username || load}</td>
                <td>{instrument?.name || load}</td>
                <td>{run?.calendar_date || load}</td>
                <td>{run?.pi || load}</td>
                <td>{assignment.priority}</td>
                <td>{assignment.status}</td>
                <td>{assignment.comment}</td>
                <td>
                  <span>
                    <IconButton
                      aria-label="delete"
                      onClick={() => {
                        deleteAssignment(assignment.id);
                      }}
                    >
                      <DeleteIcon />
                    </IconButton>
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

AssignmentList.propTypes = {
  assignments: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number,
      requester: PropTypes.shape({
        id: PropTypes.number,
        username: PropTypes.string,
      }),
      run: PropTypes.shape({
        pi: PropTypes.string,
        calendar_date: PropTypes.string,
      }),
      priority: PropTypes.string,
      status: PropTypes.string,
      comment: PropTypes.string,
    })
  ).isRequired,
};

export default AssignmentList;
