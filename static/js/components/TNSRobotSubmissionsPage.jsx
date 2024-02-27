import React, { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useParams } from "react-router-dom";
import PropTypes from "prop-types";
import makeStyles from "@mui/styles/makeStyles";

import MUIDataTable from "mui-datatables";

import { userLabel } from "./TNSRobotsPage";

import * as tnsrobotsActions from "../ducks/tnsrobots";

const useStyles = makeStyles(() => ({
  tnsrobots: {
    width: "100%",
  },
  manageButtons: {
    display: "flex",
    flexDirection: "row",
  },
}));

const TNSRobotSubmissionsPage = () => {
  const classes = useStyles();
  const dispatch = useDispatch();

  const { id } = useParams();

  const { users: allUsers } = useSelector((state) => state.users);

  const submissions = useSelector((state) => state.tnsrobots.submissions);

  const tnsrobot_submissions =
    submissions && submissions[id] ? submissions[id] : [];

  useEffect(() => {
    if (id) {
      dispatch(tnsrobotsActions.fetchTNSRobotSubmissions(id));
    }
  }, [dispatch, id]);

  const usersLookup = {};
  if (allUsers?.length > 0) {
    allUsers.forEach((u) => {
      usersLookup[u.id] = u;
    });
  }

  const columns = [
    {
      name: "id",
      label: "ID",
      options: {
        display: false,
        filter: false,
        sort: false,
      },
    },
    {
      name: "obj_id",
      label: "Source",
      options: {
        filter: false,
        sort: true,
      },
    },
    {
      name: "reporter",
      label: "Reporter",
      options: {
        filter: false,
        sort: true,
        customBodyRenderLite: (dataIndex) => {
          const { user_id } = tnsrobot_submissions[dataIndex];
          return userLabel(usersLookup[user_id]);
        },
      },
    },
    {
      name: "status",
      label: "Status",
      options: {
        filter: false,
        sort: true,
      },
    },
    {
      name: "submission_id",
      label: "Submission ID (on TNS)",
      options: {
        filter: false,
        sort: false,
      },
    },
  ];

  return (
    <div>
      <MUIDataTable
        className={classes.tnsrobots}
        title="TNS Robot Submissions"
        data={tnsrobot_submissions}
        columns={columns}
        options={{
          selectableRows: "none",
          filter: false,
          print: false,
          download: false,
          viewColumns: false,
          pagination: false,
          search: false,
        }}
      />
    </div>
  );
};

TNSRobotSubmissionsPage.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string,
  }).isRequired,
};

export default TNSRobotSubmissionsPage;
