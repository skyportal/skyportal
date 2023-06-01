import React, { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import InputLabel from "@mui/material/InputLabel";
import makeStyles from "@mui/styles/makeStyles";

import MUIDataTable from "mui-datatables";

import * as tnsrobotsActions from "../ducks/tnsrobots";

const useStyles = makeStyles(() => ({
  tnsrobots: {
    width: "100%",
  },
  container: {
    width: "99%",
    marginBottom: "1rem",
  },
}));

const TNSRobots = ({ group_id }) => {
  const classes = useStyles();
  const dispatch = useDispatch();

  const { tnsrobotList } = useSelector((state) => state.tnsrobots);

  useEffect(() => {
    const getTNSRobots = async () => {
      // Wait for the TNS robots to update before setting
      // the new default form fields, so that the TNS robots list can
      // update
      if (group_id) {
        await dispatch(
          tnsrobotsActions.fetchTNSRobots({
            groupID: group_id,
          })
        );
      }
    };
    if (tnsrobotList?.length === 0 && !tnsrobotList) {
      getTNSRobots();
    } else if (
      tnsrobotList?.length > 0 &&
      tnsrobotList[0]?.group_id !== group_id
    ) {
      getTNSRobots();
    }
  }, [dispatch, group_id, tnsrobotList]);

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
      name: "bot_name",
      label: "Bot name",
      options: {
        filter: false,
        sort: true,
      },
    },
    {
      name: "bot_id",
      label: "Bot ID",
      options: {
        filter: false,
        sort: true,
      },
    },
    {
      name: "source_group_id",
      label: "Source group ID",
      options: {
        filter: false,
        sort: true,
      },
    },
    {
      name: "auto_report_group_ids",
      label: "Auto Report",
      options: {
        filter: false,
        sort: true,
        customBodyRenderLite: (dataIndex) => {
          const auto_report = "False";
          if (tnsrobotList[dataIndex].auto_report_group_ids?.length > 0) {
            // if the group_id is in the list of auto_report_group_ids, then it is True
            if (
              tnsrobotList[dataIndex].auto_report_group_ids.includes(group_id)
            ) {
              return "True";
            }
          }
          return <span>{auto_report}</span>;
        },
      },
    },
    {
      name: "auto_reporters",
      label: "Auto Reporters",
      options: {
        filter: false,
        sort: true,
      },
    },
  ];

  return (
    <div className={classes.container}>
      <InputLabel id="tnsrobot-select-label">TNS Robots</InputLabel>
      {tnsrobotList?.length > 0 ? (
        <MUIDataTable
          className={classes.tnsrobots}
          title="TNS Robots"
          data={tnsrobotList}
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
      ) : (
        <p>No TNS robots are currently associated with this group.</p>
      )}
    </div>
  );
};

TNSRobots.propTypes = {
  group_id: PropTypes.number.isRequired,
};

export default TNSRobots;
