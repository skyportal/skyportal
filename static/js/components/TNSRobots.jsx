import React, { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import InputLabel from "@mui/material/InputLabel";
import makeStyles from "@mui/styles/makeStyles";

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
  }, [dispatch, tnsrobotList]);

  return (
    <div className={classes.container}>
      <InputLabel id="tnsrobot-select-label">TNS Robots</InputLabel>
      {tnsrobotList?.length > 0 ? (
        <ul className={classes.tnsrobots}>
          {tnsrobotList?.map((tnsrobot) => (
            <li key={tnsrobot.id}>
              <a href={tnsrobot.url} target="_blank" rel="noreferrer">
                {tnsrobot.name}
              </a>
            </li>
          ))}
        </ul>
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
