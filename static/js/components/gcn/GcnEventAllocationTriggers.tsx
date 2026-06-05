import { useState } from "react";
import { makeStyles } from "tss-react/mui";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";

import { showNotification } from "baselayer/components/Notifications";

import { useAppDispatch, useAppSelector } from "../../types/hooks";
import * as gcnEventActions from "../../ducks/gcnEvent";
import {
  useGetAllocationsQuery,
  useGetAllocationsApiObsplanQuery,
} from "../../ducks/allocations";

const useStyles = makeStyles()(() => ({
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
      marginLeft: "0.05rem",
      marginRight: "0.05rem",
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

interface GcnEventAllocationTriggersProps {
  gcnEvent: any;
  showTriggered?: boolean;
  showPassed?: boolean;
  showUnset?: boolean;
  showTitle?: boolean;
}

const GcnEventAllocationTriggers = ({
  gcnEvent,
  showTriggered = true,
  showPassed = false,
  showUnset = false,
  showTitle = false,
}: GcnEventAllocationTriggersProps) => {
  const { classes } = useStyles();
  const dispatch = useAppDispatch();

  const currentUser = useAppSelector((state) => state.profile);
  const { data: allocationListApiObsplan = [] } =
    useGetAllocationsApiObsplanQuery();
  const { data: allocationList = [] } = useGetAllocationsQuery();

  const { instrumentList } = useAppSelector((state) => state["instruments"]);

  const [selectedInstrument, setSelectedInstrument] = useState<any>(null);

  const permission =
    currentUser.permissions?.includes("System admin") ||
    currentUser.permissions?.includes("Manage allocations");

  const instNameLookUp: Record<string, any> = {};
  instrumentList?.forEach((instrumentObj: any) => {
    instNameLookUp[instrumentObj.id] = instrumentObj.name;
  });

  const allocationLookUp: Record<string, any> = {};
  // link the allocation_id to the instrument name
  if (showUnset === false) {
    // we do not need to find instruments that haven't set a triggered status
    allocationList?.forEach((allocation: any) => {
      allocationLookUp[allocation.id] =
        instNameLookUp[allocation.instrument_id];
    });
  } else {
    allocationListApiObsplan?.forEach((allocation: any) => {
      allocationLookUp[allocation.id] =
        instNameLookUp[allocation.instrument_id];
    });
  }

  const triggers = gcnEvent?.gcn_triggers || [];
  const instruments_triggered: Record<string, any> = {};

  instrumentList.forEach((instrument: any) => {
    if (
      Object.values(allocationLookUp).includes(instrument.name) &&
      !Object.keys(instruments_triggered).includes(instrument.name)
    ) {
      instruments_triggered[instrument.name] = {
        triggered: "not_set",
        allocation_triggered: [],
      };
    }
  });

  Object.keys(allocationLookUp).forEach((allocation_id) => {
    const t =
      triggers.find(
        (trigger: any) => trigger.allocation_id === parseInt(allocation_id, 10),
      ) || null;
    if (instruments_triggered[allocationLookUp[allocation_id]] === undefined) {
      instruments_triggered[allocationLookUp[allocation_id]] = {
        triggered: "not_set",
        allocation_triggered: [],
      };
    }
    if (
      t?.triggered === true &&
      instruments_triggered[allocationLookUp[allocation_id]]?.triggered ===
        "not_set"
    ) {
      instruments_triggered[allocationLookUp[allocation_id]].triggered =
        "triggered";
    } else if (
      t?.triggered === false &&
      instruments_triggered[allocationLookUp[allocation_id]]?.triggered ===
        "not_set"
    ) {
      instruments_triggered[allocationLookUp[allocation_id]].triggered =
        "passed";
    } else if (
      t !== null &&
      t?.triggered === false &&
      instruments_triggered[allocationLookUp[allocation_id]]?.triggered !==
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
    // first verify that there is an "allocation_triggered" array, if not create it
    if (instruments_triggered[allocationLookUp[allocation_id]] !== undefined) {
      instruments_triggered[
        allocationLookUp[allocation_id]
      ].allocation_triggered.push({
        triggered,
        triggeredText,
        trigger_id: t?.id || null,
        allocation: allocationListApiObsplan.find(
          (allocation: any) => allocation.id === parseInt(allocation_id, 10),
        ),
      });
    }
  });

  // now, bassed on the showTriggered, showPassed, and showUnset props, filter out the instruments_triggered object
  const filtered_instruments_triggered: Record<string, any> = {};
  Object.keys(instruments_triggered).forEach((instrument) => {
    if (
      showTriggered === false &&
      instruments_triggered[instrument].triggered === "triggered"
    ) {
      // empty
    } else if (
      showPassed === false &&
      instruments_triggered[instrument].triggered === "passed"
    ) {
      // empty
    } else if (
      showUnset === false &&
      instruments_triggered[instrument].triggered === "not_set"
    ) {
      // empty
    } else if (
      showTriggered === false &&
      showPassed === false &&
      showUnset === true &&
      instruments_triggered[instrument].triggered === "mixed"
    ) {
      // empty
    } else {
      filtered_instruments_triggered[instrument] =
        instruments_triggered[instrument];
    }
  });

  return Object.keys(filtered_instruments_triggered).length > 0 ? (
    <div className={classes.root}>
      {showTitle && <h4 className={classes.title}>Instruments triggered:</h4>}
      <div
        className={classes.chips}
        {...({ name: "gcn_triggers-chips" } as any)}
      >
        {Object.keys(filtered_instruments_triggered).map((instrument) => (
          <Chip
            size="small"
            label={instrument}
            key={instrument}
            id={`${instrument}_${filtered_instruments_triggered[instrument].triggered}`}
            clickable={permission || false}
            className={
              (classes as any)[
                filtered_instruments_triggered[instrument].triggered
              ]
            }
            onClick={() => {
              if (permission) {
                setSelectedInstrument(
                  filtered_instruments_triggered[instrument],
                );
              } else {
                dispatch(
                  showNotification(
                    "You do not have permission to edit this GCN event allocation triggers",
                    "error",
                  ),
                );
              }
            }}
          />
        ))}
      </div>
      <Dialog
        open={selectedInstrument !== null}
        onClose={() => setSelectedInstrument(null)}
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
              (allocationTrigger: any) => (
                <tr key={allocationTrigger?.allocation?.id}>
                  <td>
                    {`Allocation ${allocationTrigger.allocation.id} (PI: ${allocationTrigger.allocation.pi})`}
                  </td>
                  <td>
                    <Chip
                      size="small"
                      label={allocationTrigger.triggeredText}
                      key="trigger"
                      id={`${allocationTrigger?.allocation?.id}_current`}
                      className={(classes as any)[allocationTrigger.triggered]}
                    />
                  </td>
                  <td className={classes.chips}>
                    <Chip
                      size="small"
                      label="Triggered"
                      key="triggered"
                      id={`${allocationTrigger?.allocation?.id}_triggered`}
                      clickable
                      className={classes.triggered}
                      onClick={() => {
                        dispatch(
                          gcnEventActions.putGcnTrigger({
                            dateobs: gcnEvent.dateobs,
                            allocationID: allocationTrigger?.allocation?.id,
                            triggered: true,
                          }),
                        ).then((response: any) => {
                          if (response.status === "success") {
                            dispatch(
                              showNotification(
                                "Trigger state updated successfully",
                              ),
                            );
                            setSelectedInstrument(null);
                          } else {
                            dispatch(
                              showNotification(
                                "Error updating trigger state",
                                "error",
                              ),
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
                      id={`${allocationTrigger?.allocation?.id}_passed`}
                      clickable
                      className={classes.passed}
                      onClick={() => {
                        dispatch(
                          gcnEventActions.putGcnTrigger({
                            dateobs: gcnEvent.dateobs,
                            allocationID: allocationTrigger?.allocation?.id,
                            triggered: false,
                          }),
                        ).then((response: any) => {
                          if (response.status === "success") {
                            dispatch(
                              showNotification(
                                "Trigger state updated successfully",
                              ),
                            );
                            setSelectedInstrument(null);
                          } else {
                            dispatch(
                              showNotification(
                                "Error updating trigger state",
                                "error",
                              ),
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
                      id={`${allocationTrigger?.allocation?.id}_not-set`}
                      clickable
                      className={classes.not_set}
                      onClick={() => {
                        dispatch(
                          gcnEventActions.deleteGcnTrigger({
                            dateobs: gcnEvent.dateobs,
                            allocationID: allocationTrigger?.allocation?.id,
                          }),
                        ).then((response: any) => {
                          if (response.status === "success") {
                            dispatch(
                              showNotification(
                                "Trigger state updated successfully",
                              ),
                            );
                            setSelectedInstrument(null);
                          } else {
                            dispatch(
                              showNotification(
                                "Error updating trigger state",
                                "error",
                              ),
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
              ),
            )}
          </table>
        </DialogContent>
      </Dialog>
    </div>
  ) : null;
};

export default GcnEventAllocationTriggers;
