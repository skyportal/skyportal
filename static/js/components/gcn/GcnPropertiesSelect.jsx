import React, { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import ButtonGroup from "@mui/material/ButtonGroup";
import TextField from "@mui/material/TextField";
import InputLabel from "@mui/material/InputLabel";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import FormControl from "@mui/material/FormControl";
import Box from "@mui/material/Box";
import { Controller, useForm } from "react-hook-form";
import Button from "../Button";
import SelectWithChips from "../SelectWithChips";

import * as gcnPropertiesActions from "../../ducks/gcnProperties";

const GcnPropertiesSelect = ({
  selectedGcnProperties,
  setSelectedGcnProperties,
  conversions,
  comparators,
}) => {
  const dispatch = useDispatch();
  const gcnProperties = [
    ...(useSelector((state) => state.gcnProperties) || []),
  ].sort();
  const { handleSubmit, control, reset, getValues } = useForm();

  useEffect(() => {
    dispatch(gcnPropertiesActions.fetchGcnProperties());
  }, [dispatch]);

  const handleSubmitProperties = async () => {
    const { property, propertyComparator, propertyComparatorValue } =
      getValues();
    if (!property || !propertyComparator || !propertyComparatorValue) return;

    const value =
      conversions[property]?.FrontendToBackend(propertyComparatorValue) ||
      propertyComparatorValue;
    setSelectedGcnProperties([
      ...selectedGcnProperties,
      `${property}: ${value}: ${propertyComparator}`,
    ]);
  };

  return (
    <form
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "0.5rem",
      }}
    >
      <Box sx={{ display: "flex", gap: "0.2rem" }}>
        <Controller
          name="property"
          control={control}
          defaultValue=""
          render={({ field: { value } }) => (
            <FormControl fullWidth>
              <InputLabel>Property</InputLabel>
              <Select
                label="Property"
                value={value}
                onChange={(e) =>
                  reset({ ...getValues(), property: e.target.value })
                }
              >
                {gcnProperties?.map((prop) => (
                  <MenuItem value={prop} key={prop}>
                    {prop}
                    {conversions[prop]
                      ? ` (${conversions[prop].frontendUnit})`
                      : ""}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          )}
        />
        <Controller
          name="propertyComparator"
          control={control}
          defaultValue="eq"
          render={({ field: { value } }) => (
            <FormControl fullWidth>
              <InputLabel>Comparator</InputLabel>
              <Select
                label="Comparator"
                value={value}
                onChange={(e) =>
                  reset({ ...getValues(), propertyComparator: e.target.value })
                }
              >
                {Object.keys(comparators).map((key) => (
                  <MenuItem key={key} value={key}>
                    {comparators[key]}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          )}
        />
        <Controller
          name="propertyComparatorValue"
          control={control}
          defaultValue="0.0"
          render={({ field }) => (
            <TextField {...field} label="Value" placeholder="0.0" />
          )}
        />
      </Box>
      <Box sx={{ display: "flex", gap: "0.2rem" }}>
        <ButtonGroup variant="outlined" color="primary">
          <Button
            variant="outlined"
            primary
            onClick={handleSubmit(handleSubmitProperties)}
          >
            Add
          </Button>
          <Button variant="outlined" primary onClick={reset}>
            Reset
          </Button>
        </ButtonGroup>
        <SelectWithChips
          label="Gcn Properties"
          id="selectGcns"
          initValue={selectedGcnProperties}
          onChange={(e) => setSelectedGcnProperties(e.target.value)}
          options={selectedGcnProperties}
        />
      </Box>
    </form>
  );
};

GcnPropertiesSelect.propTypes = {
  selectedGcnProperties: PropTypes.arrayOf(PropTypes.string).isRequired,
  setSelectedGcnProperties: PropTypes.func.isRequired,
  conversions: PropTypes.oneOfType([PropTypes.object]).isRequired,
  comparators: PropTypes.objectOf(PropTypes.string).isRequired,
};

export default GcnPropertiesSelect;
