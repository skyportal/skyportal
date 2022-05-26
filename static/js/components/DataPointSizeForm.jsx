import React, { useState, useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import { TextField } from "@material-ui/core";
import UserPreferencesHeader from "./UserPreferencesHeader";
import * as profileActions from "../ducks/profile";

const DataPointSizeForm = () => {
  const [errorText, setErrorText] = useState("");
  const dispatch = useDispatch();
  const { photometryDataPointSize } = useSelector(
    (state) => state.profile.preferences
  );
  const [dataPointSize, setDataPointSize] = useState(4);

  useEffect(() => {
    setDataPointSize(photometryDataPointSize || 4);
  }, [photometryDataPointSize]);

  const onChange = (event) => {
    setDataPointSize(event.target.value);
    if (
      parseInt(event.target.value, 10) >= 1 &&
      parseInt(event.target.value, 10) <= 60
    ) {
      setErrorText("");
      const prefs = {
        photometryDataPointSize: parseFloat(event.target.value),
      };
      dispatch(profileActions.updateUserPreferences(prefs));
    } else {
      setErrorText("Size must be between 1 and 60 inclusive.");
    }
  };
  return (
    <>
      <UserPreferencesHeader
        title="Data Point Size"
        popupText="Size of data points on photometry plot. Ranges from 1-60."
      />
      <TextField
        label="Size"
        type="number"
        name="photometryDataPointSize"
        onChange={onChange}
        error={Boolean(errorText)}
        helperText={errorText}
        value={dataPointSize}
      />
    </>
  );
};

export default DataPointSizeForm;
