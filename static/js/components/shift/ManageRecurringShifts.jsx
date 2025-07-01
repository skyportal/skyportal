import React, { useEffect, useState } from "react";
import { useDispatch } from "react-redux";
import PropTypes from "prop-types";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import InputLabel from "@mui/material/InputLabel";
import FormControl from "@mui/material/FormControl";
import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";
import ShiftUsersSelect from "./ShiftUsersSelect";
import { deleteShift } from "../../ducks/shift";

import * as shiftActions from "../../ducks/shift";

const ManageRecurringShifts = ({ shiftList }) => {
  const [recurringShiftToUpdate, setRecurringShiftToUpdate] = useState(null);
  const [shiftIdSelect, setShiftIdSelect] = useState(null);
  const dispatch = useDispatch();
  const recurringShift = {};

  // Load the details of the first shift of the selected recurring group of shifts
  useEffect(() => {
    if (!shiftIdSelect) return;
    dispatch(shiftActions.fetchShift(shiftIdSelect)).then((result) => {
      if (result.status === "success") {
        setRecurringShiftToUpdate(result.data);
      } else {
        dispatch(showNotification("Failed to fetch shift", "error"));
      }
    });
  }, [dispatch, shiftIdSelect, shiftList]);

  const getBaseName = (shift) => {
    const match = shift.name.match(/^(.*)\s+(\d+)\/(\d+)$/);
    return match ? match[1].trim() : null;
  };

  const getRecurringShifts = (oneRecurringShift) => {
    const baseName = getBaseName(oneRecurringShift);
    if (!baseName) return null;
    return [
      oneRecurringShift,
      ...shiftList.filter(
        (shift) =>
          shift.name !== oneRecurringShift.name &&
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

  const deleteRecurringShifts = (oneRecurringShift) => {
    if (!oneRecurringShift) {
      return;
    }
    const shiftsToDelete = getRecurringShifts(oneRecurringShift);
    if (!shiftsToDelete?.length) return;

    dispatch({ type: "skyportal/FETCH_SHIFT_OK", data: {} });

    shiftsToDelete.forEach((shift) => {
      dispatch(deleteShift(shift.id)).then((result) => {
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
          value={shiftIdSelect}
          onChange={(e) => setShiftIdSelect(e.target.value)}
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
            shiftsToManage={getRecurringShifts(recurringShiftToUpdate)}
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

ManageRecurringShifts.propTypes = {
  shiftList: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number,
      name: PropTypes.string,
      end_date: PropTypes.string,
    }),
  ).isRequired,
};

export default ManageRecurringShifts;
