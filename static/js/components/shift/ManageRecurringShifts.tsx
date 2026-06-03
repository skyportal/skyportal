import { useEffect, useState } from "react";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import InputLabel from "@mui/material/InputLabel";
import FormControl from "@mui/material/FormControl";
import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";
import ShiftUsersSelect from "./ShiftUsersSelect";
import { useAppDispatch } from "../../types/hooks";
import * as shiftsActions from "../../ducks/shifts";

interface Shift {
  id: number;
  name: string;
  end_date: string | Date;
  group?: any;
}

interface ManageRecurringShiftsProps {
  shiftList: Shift[];
}

const ManageRecurringShifts = ({ shiftList }: ManageRecurringShiftsProps) => {
  const [recurringShiftToUpdate, setRecurringShiftToUpdate] =
    useState<Shift | null>(null);
  const [shiftIdSelect, setShiftIdSelect] = useState<number | null>(null);
  const dispatch = useAppDispatch();
  const recurringShift: Record<string, Shift> = {};

  // Load the details of the first shift of the selected recurring group of shifts
  useEffect(() => {
    if (!shiftIdSelect) setRecurringShiftToUpdate(null);

    const selectedShift = shiftList.find((shift) => shift.id === shiftIdSelect);
    // If the selected shift has not the group property, we fetch the shift details
    if (selectedShift && !selectedShift.group) {
      dispatch(shiftsActions.fetchShift(shiftIdSelect!));
    }
    // If the selected shift has the group property, we set it as the recurring shift to update
    if (selectedShift?.group) {
      setRecurringShiftToUpdate(selectedShift);
    }
  }, [dispatch, shiftIdSelect, shiftList]);

  const getBaseName = (shift: Shift) => {
    const match = shift.name.match(/^(.*)\s+(\d+)\/(\d+)$/);
    return match?.[1] ? match[1].trim() : null;
  };

  const getRecurringShifts = (oneRecurringShift: Shift) => {
    const baseName = getBaseName(oneRecurringShift);
    if (!baseName) return null;
    return [
      oneRecurringShift,
      ...shiftList.filter(
        (shift) =>
          shift.id !== oneRecurringShift.id &&
          shift.name.startsWith(baseName) &&
          /\s\d+\/\d+$/.test(shift.name),
      ),
    ];
  };

  for (const shift of shiftList) {
    const baseName = getBaseName(shift);
    if (!baseName) continue;
    if (new Date(shift.end_date) <= new Date()) continue;
    if (recurringShift[baseName]) continue;

    recurringShift[baseName] = shift;
  }

  const deleteRecurringShifts = (oneRecurringShift: Shift | null) => {
    if (!oneRecurringShift) {
      return;
    }
    const shiftsToDelete = getRecurringShifts(oneRecurringShift);
    setShiftIdSelect(null);
    if (!shiftsToDelete?.length) return;

    shiftsToDelete.forEach((shift) => {
      dispatch(shiftsActions.deleteShift(shift.id)).then((result: any) => {
        if (result.status === "success") {
          dispatch(showNotification("Shift deleted"));
        }
      });
    });
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "1rem",
        width: "100%",
        marginTop: "1rem",
      }}
    >
      <FormControl>
        <InputLabel id="recurring-shift-select-label">
          Select the recurring shift to update
        </InputLabel>
        <Select
          labelId="recurring-shift-select-label"
          label="Select the recurring shift to update"
          value={shiftIdSelect || ""}
          onChange={(e: any) => setShiftIdSelect(e.target.value)}
          style={{ minWidth: "100%" }}
        >
          {Object.entries(recurringShift).map(([baseName, shift]) => (
            <MenuItem key={baseName} value={shift.id}>
              {baseName}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
      {recurringShiftToUpdate && (
        <>
          <ShiftUsersSelect
            shiftsToManage={
              getRecurringShifts(recurringShiftToUpdate) ?? undefined
            }
            usersType="admins"
          />
          <Button
            variant="outlined"
            color="error"
            onClick={() => deleteRecurringShifts(recurringShiftToUpdate)}
          >
            {`Delete all recurring shifts "${getBaseName(
              recurringShiftToUpdate,
            )}"`}
          </Button>
        </>
      )}
    </div>
  );
};

export default ManageRecurringShifts;
