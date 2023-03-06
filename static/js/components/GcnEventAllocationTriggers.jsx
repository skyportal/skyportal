import React, { useState } from "react";
import Chip from "@mui/material/Chip";
import PropTypes from "prop-types";
import makeStyles from "@mui/styles/makeStyles";
import { useSelector, useDispatch } from "react-redux";

import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";

import { showNotification } from "baselayer/components/Notifications";

import * as gcnEventActions from "../ducks/gcnEvent";

const useStyles = makeStyles(() => ({
  root: {
    margin: "0",
    padding: "0",
    display: "flex",
    flexDirection: "row",
    alignItems: "center",
  },
  title: {
    margin: 0,
    marginRight: "0.45rem",
    padding: "0",
  },
  chips: {
    padding: "0",
    margin: "0",
    "& > div": {
      marginTop: 0,
      marginBottom: 0,
      marginLeft: "0.1rem",
      marginRight: "0.1rem",
    },
  },
  addIcon: {
    fontSize: "1rem",
  },

  triggered: {
    background: "#468847!important", // green
  },
  passed: {
    background: "#b94a48!important", // red
  },
  not_set: {
    background: "#999999!important", // grey
  },
  mixed: {
    background: "linear-gradient(120deg, #468847 50%, #d54f4d 50%)",
  },
  allocationTable: {
    borderCollapse: "collapse",
    width: "100%",
    "& th": {
      border: "1px solid #dddddd",
      textAlign: "left",
      padding: "8px",
    },
    "& td": {
      border: "1px solid #dddddd",
      textAlign: "left",
      padding: "8px",
    },
  },

  allocationTrigger: {
    display: "flex",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
}));

const GcnEventAllocationTriggers = ({ gcnEvent }) => {
  const classes = useStyles();
  const dispatch = useDispatch();

  const currentUser = useSelector((state) => state.profile);
  const { allocationListApiObsplan } = useSelector(
    (state) => state.allocations
  );
  const { instrumentList } = useSelector((state) => state.instruments);

  const [selectedInstrument, setSelectedInstrument] = useState(null);

  const permission =
    currentUser.permissions?.includes("System admin") ||
    currentUser.permissions?.includes("Manage allocations");

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
  // created a nested object with the instrument as the key, and the value is an array of all the allocations for that instrument with the triggered state
  const triggers = gcnEvent?.gcn_triggers || [];
  const instruments_triggered = {};
  instrumentList.forEach((instrument) => {
    // if there is any allocation for this instrument, add it to the object
    if (Object.values(allocationLookUp).includes(instrument.name)) {
      instruments_triggered[instrument.name] = {
        triggered: "not_set",
        allocation_triggered: [],
      };
    }
  });

  // for each key in the allocationLookUp object
  Object.keys(allocationLookUp).forEach((allocation_id) => {
    const t =
      triggers.find(
        (trigger) => trigger.allocation_id === parseInt(allocation_id, 10)
      ) || null;

    if (
      t?.triggered === true &&
      instruments_triggered[allocationLookUp[allocation_id]].triggered ===
        "not_set"
    ) {
      instruments_triggered[allocationLookUp[allocation_id]].triggered =
        "triggered";
    } else if (
      t?.triggered === false &&
      instruments_triggered[allocationLookUp[allocation_id]].triggered ===
        "not_set"
    ) {
      instruments_triggered[allocationLookUp[allocation_id]].triggered =
        "passed";
    } else if (
      t === null &&
      instruments_triggered[allocationLookUp[allocation_id]].triggered ===
        "not_set"
    ) {
      instruments_triggered[allocationLookUp[allocation_id]].triggered =
        "not_set";
    } else if (
      t !== null &&
      instruments_triggered[allocationLookUp[allocation_id]].triggered !==
        "not_set"
    ) {
      instruments_triggered[allocationLookUp[allocation_id]].triggered =
        "mixed";
    }

    let triggered = "not_set";
    let triggeredText = "Not set";
    if (t?.triggered === true) {
      triggered = "triggered";
      triggeredText = "Triggered";
    } else if (t?.triggered === false) {
      triggered = "passed";
      triggeredText = "Passed";
    }
    instruments_triggered[
      allocationLookUp[allocation_id]
    ].allocation_triggered.push({
      triggered,
      triggeredText,
      trigger_id: t?.id || null,
      allocation: allocationListApiObsplan.find(
        (allocation) => allocation.id === parseInt(allocation_id, 10)
      ),
    });
  });

  return Object.keys(instruments_triggered).length > 0 ? (
    <div className={classes.root}>
      <h4 className={classes.title}>Instruments triggered:</h4>
      <div className={classes.chips} name="gcn_triggers-chips">
        {Object.keys(instruments_triggered).map((instrument) => (
          <Chip
            size="small"
            label={instrument}
            key={instrument}
            clickable={permission || false}
            className={classes[instruments_triggered[instrument].triggered]}
            onClick={() => {
              setSelectedInstrument(instruments_triggered[instrument]);
            }}
          />
        ))}
      </div>
      <Dialog
        open={selectedInstrument !== null}
        onClose={() => {
          setSelectedInstrument(null);
        }}
        style={{ position: "fixed" }}
      >
        <DialogTitle>Change Trigger state</DialogTitle>
        <DialogContent>
          <table className={classes.allocationTable}>
            <tr>
              <th>Allocation</th>
              <th>Current state</th>
              <th>Edit</th>
            </tr>
            {selectedInstrument?.allocation_triggered.map(
              (allocationTrigger) => (
                <tr key={allocationTrigger?.allocation?.id}>
                  <td>
                    {`Allocation ${allocationTrigger.allocation.id} (PI: ${allocationTrigger.allocation.pi})`}
                  </td>
                  <td>
                    <Chip
                      size="small"
                      label={allocationTrigger.triggeredText}
                      key="trigger"
                      className={classes[allocationTrigger.triggered]}
                    />
                  </td>
                  <td className={classes.chips}>
                    <Chip
                      size="small"
                      label="Triggered"
                      key="triggered"
                      clickable
                      className={classes.triggered}
                      onClick={() => {
                        dispatch(
                          gcnEventActions.putGcnTrigger({
                            dateobs: gcnEvent.dateobs,
                            allocationID: allocationTrigger?.allocation?.id,
                            triggered: true,
                          })
                        ).then((response) => {
                          if (response.status === "success") {
                            dispatch(
                              showNotification(
                                "Trigger state updated successfully"
                              )
                            );
                            setSelectedInstrument(null);
                          } else {
                            dispatch(
                              showNotification(
                                "Error updating trigger state",
                                "error"
                              )
                            );
                          }
                        });
                      }}
                      style={{
                        display:
                          allocationTrigger?.triggered === "triggered"
                            ? "none"
                            : "inline-block",
                      }}
                    />
                    <Chip
                      size="small"
                      label="Passed"
                      key="passed"
                      clickable
                      className={classes.passed}
                      onClick={() => {
                        dispatch(
                          gcnEventActions.putGcnTrigger({
                            dateobs: gcnEvent.dateobs,
                            allocationID: allocationTrigger?.allocation?.id,
                            triggered: false,
                          })
                        ).then((response) => {
                          if (response.status === "success") {
                            dispatch(
                              showNotification(
                                "Trigger state updated successfully"
                              )
                            );
                            setSelectedInstrument(null);
                          } else {
                            dispatch(
                              showNotification(
                                "Error updating trigger state",
                                "error"
                              )
                            );
                          }
                        });
                      }}
                      style={{
                        display:
                          allocationTrigger?.triggered === "passed"
                            ? "none"
                            : "inline-block",
                      }}
                    />
                    <Chip
                      size="small"
                      label="Not Set"
                      key="not-set"
                      clickable
                      className={classes.not_set}
                      onClick={() => {
                        dispatch(
                          gcnEventActions.deleteGcnTrigger({
                            dateobs: gcnEvent.dateobs,
                            allocationID: allocationTrigger?.allocation?.id,
                          })
                        ).then((response) => {
                          if (response.status === "success") {
                            dispatch(
                              showNotification(
                                "Trigger state updated successfully"
                              )
                            );
                            setSelectedInstrument(null);
                          } else {
                            dispatch(
                              showNotification(
                                "Error updating trigger state",
                                "error"
                              )
                            );
                          }
                        });
                      }}
                      style={{
                        display:
                          allocationTrigger?.triggered === "not_set"
                            ? "none"
                            : "inline-block",
                      }}
                    />
                  </td>
                </tr>
              )
            )}
          </table>
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
