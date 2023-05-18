import React, { useState, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import InputLabel from "@mui/material/InputLabel";
import makeStyles from "@mui/styles/makeStyles";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import { showNotification } from "baselayer/components/Notifications";
import * as sourceActions from "../ducks/source";
import * as tnsrobotsActions from "../ducks/tnsrobots";

const useStyles = makeStyles(() => ({
  chips: {
    display: "flex",
    flexWrap: "wrap",
  },
  chip: {
    margin: 2,
  },
  tnsrobotSelect: {
    width: "100%",
  },
  tnsrobotSelectItem: {
    whiteSpace: "break-spaces",
  },
  container: {
    width: "99%",
    marginBottom: "1rem",
  },
}));

const TNSATForm = ({ obj_id }) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const groups = useSelector((state) => state.groups.userAccessible);
  const currentUser = useSelector((state) => state.profile);

  const { tnsrobotList } = useSelector((state) => state.tnsrobots);
  const [selectedTNSRobotId, setSelectedTNSRobotId] = useState(null);

  const [submissionRequestInProcess, setSubmissionRequestInProcess] =
    useState(false);
  const groupIDToName = {};
  groups?.forEach((g) => {
    groupIDToName[g.id] = g.name;
  });

  useEffect(() => {
    const getTNSRobots = async () => {
      // Wait for the TNS robots to update before setting
      // the new default form fields, so that the TNS robots list can
      // update

      const result = await dispatch(tnsrobotsActions.fetchTNSRobots());

      const { data } = result;
      setSelectedTNSRobotId(data[0]?.id);
    };
    if (tnsrobotList?.length === 0 && !tnsrobotList) {
      getTNSRobots();
    } else if (tnsrobotList?.length > 0 && !selectedTNSRobotId) {
      setSelectedTNSRobotId(tnsrobotList[0]?.id);
    }

    // Don't want to reset everytime the component rerenders and
    // the defaultStartDate is updated, so ignore ESLint here
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dispatch, setSelectedTNSRobotId, tnsrobotList]);

  // need to check both of these conditions as selectedTNSRobotId is
  // initialized to be null and useEffect is not called on the first
  // render to update it, so it can be null even if tnsrobotList is not
  // empty.
  if (tnsrobotList.length === 0 || !selectedTNSRobotId) {
    return <h3>No TNS robots available...</h3>;
  }

  const handleSubmit = async ({ formData }) => {
    setSubmissionRequestInProcess(true);
    formData.tnsrobotID = selectedTNSRobotId;
    const result = await dispatch(sourceActions.addSourceTNS(obj_id, formData));
    setSubmissionRequestInProcess(false);
    if (result.status === "success") {
      dispatch(showNotification("TNS saved"));
    }
  };

  const tnsrobotLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  tnsrobotList?.forEach((tnsrobot) => {
    tnsrobotLookUp[tnsrobot.id] = tnsrobot;
  });

  const handleSelectedTNSRobotChange = (e) => {
    setSelectedTNSRobotId(e.target.value);
  };

  const formSchema = {
    description: "Add TNS",
    type: "object",
    properties: {
      reporters: {
        type: "string",
        title: "Reporters",
        default: `${currentUser.first_name} ${currentUser.last_name} on behalf of...`,
      },
      transientComment: {
        type: "string",
        title: "Transient Comment",
      },
    },
  };

  return (
    <div className={classes.container}>
      <InputLabel id="tnsrobotSelectLabel">TNS Robot</InputLabel>
      <Select
        inputProps={{ MenuProps: { disableScrollLock: true } }}
        labelId="tnsrobotSelectLabel"
        value={selectedTNSRobotId}
        onChange={handleSelectedTNSRobotChange}
        name="tnsrobotSelect"
        className={classes.tnsrobotSelect}
      >
        {tnsrobotList?.map((tnsrobot) => (
          <MenuItem
            value={tnsrobot.id}
            key={tnsrobot.id}
            className={classes.tnsrobotSelectItem}
          >
            {`${tnsrobot.bot_name}`}
          </MenuItem>
        ))}
      </Select>
      <div data-testid="tnsrobot-form">
        <Form
          schema={formSchema}
          validator={validator}
          onSubmit={handleSubmit}
          disabled={submissionRequestInProcess}
        />
      </div>
    </div>
  );
};

TNSATForm.propTypes = {
  obj_id: PropTypes.string.isRequired,
};

export default TNSATForm;
