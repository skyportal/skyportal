import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import EditIcon from "@mui/icons-material/Edit";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import InputLabel from "@mui/material/InputLabel";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import makeStyles from "@mui/styles/makeStyles";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";
import * as sourceActions from "../ducks/source";
import * as tnsrobotsActions from "../ducks/tnsrobots";

dayjs.extend(utc);

const useStyles = makeStyles(() => ({
  saveButton: {
    textAlign: "center",
    margin: "1rem",
  },
  editIcon: {
    height: "0.75rem",
    cursor: "pointer",
  },
}));

const UpdateSourceTNS = ({ source }) => {
  const classes = useStyles();
  const dispatch = useDispatch();

  const [dialogOpen, setDialogOpen] = useState(false);
  const groups = useSelector((state) => state.groups.userAccessible);

  const { tnsrobotList } = useSelector((state) => state.tnsrobots);
  const [selectedTNSRobotId, setSelectedTNSRobotId] = useState(null);

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
    formData.tnsrobotID = selectedTNSRobotId;
    dispatch(sourceActions.addTNS(source.id, formData)).then((response) => {
      if (response.status === "success") {
        dispatch(showNotification("Successfully queried TNS"));
      } else {
        dispatch(showNotification("Failed to query TNS", "error"));
      }
    });
  };

  const tnsrobotLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  tnsrobotList?.forEach((tnsrobot) => {
    tnsrobotLookUp[tnsrobot.id] = tnsrobot;
  });

  const handleSelectedTNSRobotChange = (e) => {
    setSelectedTNSRobotId(e.target.value);
  };

  const tnsFormSchema = {
    type: "object",
    properties: {
      radius: {
        type: "number",
        title: "Search radius [arcsec]",
        default: 2.0,
      },
    },
  };

  return (
    <>
      <EditIcon
        data-testid="updateTNSIconButton"
        fontSize="small"
        className={classes.editIcon}
        onClick={() => {
          setDialogOpen(true);
        }}
      />
      <Dialog
        open={dialogOpen}
        onClose={() => {
          setDialogOpen(false);
        }}
        style={{ position: "fixed" }}
      >
        <DialogTitle>Query TNS</DialogTitle>
        <DialogContent>
          <div>
            <div>
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
            </div>
            <div>
              <Form
                schema={tnsFormSchema}
                validator={validator}
                onSubmit={handleSubmit}
              />
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

UpdateSourceTNS.propTypes = {
  source: PropTypes.shape({
    id: PropTypes.string,
    tns_name: PropTypes.string,
  }).isRequired,
};

export default UpdateSourceTNS;
