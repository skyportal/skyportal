import { useGetProfileQuery } from "../../ducks/profile";
import { useState } from "react";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import {
  getContrastRatio,
  type PaletteColor,
  type Theme,
} from "@mui/material/styles";

import { showNotification } from "baselayer/components/Notifications";

import { useAppDispatch } from "../../types/hooks";
import {
  usePutGcnTriggerMutation,
  useDeleteGcnTriggerMutation,
} from "../../ducks/gcnEvent";
import {
  useGetAllocationsQuery,
  useGetAllocationsApiObsplanQuery,
} from "../../ducks/allocations";
import { useGetInstrumentsQuery } from "../../ducks/instruments";
import Button from "../Button";
import softButtonsSx from "../softButtons";
import EventInfoRow from "./EventInfoRow";

const STATE_LABELS: Record<string, string> = {
  triggered: "Triggered",
  passed: "Passed",
  not_set: "Not set",
};

const STATE_OPTIONS = [
  { state: "triggered", idSuffix: "triggered", value: true },
  { state: "passed", idSuffix: "passed", value: false },
  { state: "not_set", idSuffix: "not-set", value: null },
];

const stateChipSx = (state: string) => (theme: Theme) => {
  if (state === "not_set") return { fontWeight: 500 };
  const { success, error, common } = theme.palette;
  const shade = ({ main, dark }: PaletteColor) =>
    getContrastRatio(main, common.white) >= 3 ? main : dark;
  const green = shade(success);
  const red = shade(error);
  const background =
    state === "mixed"
      ? `linear-gradient(120deg, ${green} 50%, ${red} 50%)`
      : state === "triggered"
        ? green
        : red;
  return {
    fontWeight: 500,
    color: common.white,
    background,
    "&.MuiChip-clickable:hover": { background, filter: "brightness(0.9)" },
  };
};

const dialogSlotProps = {
  paper: {
    sx: (theme: Theme) => ({ borderRadius: "12px", ...softButtonsSx(theme) }),
  },
};

const tableSx = {
  "& .MuiTableCell-root": { borderColor: "divider", px: 1, py: 1 },
  "& .MuiTableCell-head": {
    py: 0.5,
    color: "text.secondary",
    fontSize: "0.75rem",
    fontWeight: 500,
  },
  "& .MuiTableBody-root .MuiTableRow-root:last-of-type .MuiTableCell-root": {
    borderBottom: 0,
  },
};

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
  const dispatch = useAppDispatch();
  const [putGcnTrigger] = usePutGcnTriggerMutation();
  const [deleteGcnTrigger] = useDeleteGcnTriggerMutation();

  const { data: currentUser } = useGetProfileQuery();
  const { data: allocationListApiObsplan = [] } =
    useGetAllocationsApiObsplanQuery();
  const { data: allocationList = [] } = useGetAllocationsQuery();

  const { data: instrumentList = [] } = useGetInstrumentsQuery();

  const [selectedInstrument, setSelectedInstrument] = useState<string | null>(
    null,
  );
  const [pending, setPending] = useState(false);

  const permission =
    currentUser?.permissions?.includes("System admin") ||
    currentUser?.permissions?.includes("Manage allocations");

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
    if (t?.triggered === true) {
      triggered = "triggered";
    } else if (t?.triggered === false) {
      triggered = "passed";
    }
    // first verify that there is an "allocation_triggered" array, if not create it
    if (instruments_triggered[allocationLookUp[allocation_id]] !== undefined) {
      instruments_triggered[
        allocationLookUp[allocation_id]
      ].allocation_triggered.push({
        triggered,
        trigger_id: t?.id || null,
        allocation: [...allocationListApiObsplan, ...allocationList].find(
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

  if (!Object.keys(filtered_instruments_triggered).length) return null;

  const updateTrigger = (allocationID: number, triggered: boolean | null) => {
    setPending(true);
    const request: Promise<unknown> =
      triggered === null
        ? deleteGcnTrigger({ dateobs: gcnEvent.dateobs, allocationID }).unwrap()
        : putGcnTrigger({
            dateobs: gcnEvent.dateobs,
            allocationID,
            triggered,
          }).unwrap();
    request
      .then(() => {
        dispatch(showNotification("Trigger state updated successfully"));
        setSelectedInstrument(null);
      })
      .catch(() => {
        dispatch(showNotification("Error updating trigger state", "error"));
      })
      .finally(() => setPending(false));
  };

  const selectedAllocations =
    (selectedInstrument &&
      instruments_triggered[selectedInstrument]?.allocation_triggered) ||
    [];

  const content = (
    <>
      <Box
        sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}
        {...({ name: "gcn_triggers-chips" } as any)}
      >
        {Object.keys(filtered_instruments_triggered).map((instrument) => (
          <Chip
            size="small"
            label={instrument}
            key={instrument}
            id={`${instrument}_${filtered_instruments_triggered[instrument].triggered}`}
            clickable={permission || false}
            sx={stateChipSx(
              filtered_instruments_triggered[instrument].triggered,
            )}
            onClick={() => {
              if (permission) {
                setSelectedInstrument(instrument);
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
      </Box>
      <Dialog
        open={selectedAllocations.length > 0}
        onClose={() => setSelectedInstrument(null)}
        slotProps={dialogSlotProps}
      >
        <DialogTitle>{selectedInstrument} trigger state</DialogTitle>
        <DialogContent sx={{ pb: 0 }}>
          <Table size="small" sx={tableSx}>
            <TableHead>
              <TableRow>
                <TableCell>Allocation</TableCell>
                <TableCell>State</TableCell>
                <TableCell align="right">Set to</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {selectedAllocations.map((allocationTrigger: any) => {
                const { allocation } = allocationTrigger;
                return (
                  <TableRow key={allocation?.id}>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontWeight: 500 }}>
                        Allocation {allocation?.id}
                      </Typography>
                      <Typography
                        variant="caption"
                        component="div"
                        color="text.secondary"
                      >
                        {[`PI: ${allocation?.pi}`, allocation?.proposal_id]
                          .filter(Boolean)
                          .join(" · ")}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        label={STATE_LABELS[allocationTrigger.triggered]}
                        id={`${allocation?.id}_current`}
                        sx={stateChipSx(allocationTrigger.triggered)}
                      />
                    </TableCell>
                    <TableCell>
                      <Box
                        sx={{
                          display: "flex",
                          justifyContent: "flex-end",
                          gap: 0.75,
                        }}
                      >
                        {STATE_OPTIONS.filter(
                          ({ state }) => state !== allocationTrigger.triggered,
                        ).map(({ state, idSuffix, value }) => (
                          <Button
                            key={state}
                            secondary
                            size="small"
                            id={`${allocation?.id}_${idSuffix}`}
                            disabled={pending}
                            onClick={() => updateTrigger(allocation?.id, value)}
                          >
                            {STATE_LABELS[state]}
                          </Button>
                        ))}
                      </Box>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </DialogContent>
        <DialogActions>
          <Button secondary onClick={() => setSelectedInstrument(null)}>
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
  return showTitle ? (
    <EventInfoRow label="Triggered">{content}</EventInfoRow>
  ) : (
    <Box sx={{ display: "flex", alignItems: "center" }}>{content}</Box>
  );
};

export default GcnEventAllocationTriggers;
