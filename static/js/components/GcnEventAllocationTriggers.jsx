import React, { useState } from "react";
import Chip from "@mui/material/Chip";
import PropTypes from "prop-types";
import makeStyles from "@mui/styles/makeStyles";
import { useSelector, useDispatch } from "react-redux";

import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";

// import { showNotification } from "baselayer/components/Notifications";

import * as gcnEventActions from "../ducks/gcnEvent";

const useStyles = makeStyles(() => ({
  root: {
    margin: "0",
    padding: "0",
  },
  title: {
    margin: "0",
    padding: "0",
  },
  chips: {
    padding: "0",
    margin: "0",
    "& > div": {
      marginTop: "0",
      margin: "0.25rem",
    },
  },
  addIcon: {
    fontSize: "1rem",
  },

  true: {
    background: "#468847!important", // green
  },
  false: {
    background: "#b94a48!important", // red
  },
  null: {
    background: "#999999!important", // grey
  },
}));

const GcnEventAllocationTriggers = ({ gcnEvent }) => {
  const classes = useStyles();
  const dispatch = useDispatch();

  const { allocationListApiObsplan } = useSelector(
    (state) => state.allocations
  );

  const { instrumentList } = useSelector((state) => state.instruments);

  const [selectedTrigger, setSelectedTrigger] = useState(null);

  const instNameLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  instrumentList?.forEach((instrumentObj) => {
    instNameLookUp[instrumentObj.id] = instrumentObj.name;
  });

  const allocationLookUp = {};
  // link the allocation_id to the instrument name
  // eslint-disable-next-line no-unused-expressions
  allocationListApiObsplan?.forEach((allocation) => {
    allocationLookUp[allocation.id] = instNameLookUp[allocation.instrument_id];
  });

  const triggers = gcnEvent.gcn_triggers;

  // for allocations that dont have a trigger, add a trigger
  allocationListApiObsplan.forEach((allocation) => {
    if (!triggers.some((trigger) => trigger.allocation_id === allocation.id)) {
      triggers.push({
        id: null,
        allocation_id: allocation.id,
        dateobs: gcnEvent.dateobs,
        triggered: null,
      });
    }
  });

  return Object.keys(allocationLookUp).length > 0 ? (
    <div className={classes.root}>
      <div className={classes.chips} name="gcn_triggers-chips">
        {triggers.map((trigger) => (
          <Chip
            size="small"
            label={allocationLookUp[trigger.allocation_id]}
            key={trigger.id}
            clickable
            className={classes[trigger.triggered]}
            onClick={() => {
              setSelectedTrigger(trigger);
            }}
          />
        ))}
      </div>
      <Dialog
        open={selectedTrigger !== null}
        onClose={() => {
          setSelectedTrigger(null);
        }}
        style={{ position: "fixed" }}
      >
        <DialogTitle>Change Trigger state</DialogTitle>
        <DialogContent>
          <div>
            {/* display 3 chips, one green to set to triggered */}
            {/* one red to set to not triggered */}
            {/* one grey to set to null */}
            {/* hide the chips that are already set to that state */}

            <Chip
              size="small"
              label="Triggered"
              key="triggered"
              clickable
              className={classes.true}
              onClick={() => {
                dispatch(
                  gcnEventActions.putGcnTrigger({
                    dateobs: gcnEvent.dateobs,
                    allocationID: selectedTrigger.allocation_id,
                    triggered: true,
                  })
                );

                setSelectedTrigger(null);
              }}
              style={{
                display:
                  selectedTrigger?.triggered === true ? "none" : "inline-block",
              }}
            />
            <Chip
              size="small"
              label="Passed"
              key="not-triggered"
              clickable
              className={classes.false}
              onClick={() => {
                dispatch(
                  gcnEventActions.putGcnTrigger({
                    dateobs: gcnEvent.dateobs,
                    allocationID: selectedTrigger.allocation_id,
                    triggered: false,
                  })
                );
                setSelectedTrigger(null);
              }}
              style={{
                display:
                  selectedTrigger?.triggered === false
                    ? "none"
                    : "inline-block",
              }}
            />
            <Chip
              size="small"
              label="Not Set"
              key="not-set"
              clickable
              className={classes.null}
              onClick={() => {
                dispatch(
                  gcnEventActions.deleteGcnTrigger({
                    dateobs: gcnEvent.dateobs,
                    allocationID: selectedTrigger.allocation_id,
                  })
                );
                setSelectedTrigger(null);
              }}
              style={{
                display:
                  selectedTrigger?.triggered === null ? "none" : "inline-block",
              }}
            />
          </div>
        </DialogContent>
      </Dialog>
    </div>
  ) : null;
};

GcnEventAllocationTriggers.propTypes = {
  gcnEvent: PropTypes.shape({
    dateobs: PropTypes.string,
    gcn_triggers: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number,
        allocation_id: PropTypes.number,
        dateobs: PropTypes.string,
        triggered: PropTypes.bool,
      })
    ),
  }).isRequired,
};

export default GcnEventAllocationTriggers;
