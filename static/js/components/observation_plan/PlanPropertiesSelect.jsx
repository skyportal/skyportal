import React from "react";
import PropTypes from "prop-types";
import ButtonGroup from "@mui/material/ButtonGroup";
import TextField from "@mui/material/TextField";
import InputLabel from "@mui/material/InputLabel";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import Box from "@mui/material/Box";
import FormControl from "@mui/material/FormControl";
import { Controller, useForm } from "react-hook-form";
import Button from "../Button";
import SelectWithChips from "../SelectWithChips";

const PlanPropertiesSelect = ({
  selectedPlanProperties,
  setSelectedPlanProperties,
  comparators,
}) => {
  let planProperties = [
    "area",
    "num_observations",
    "probability",
    "tot_time_with_overhead",
    "total_time",
  ];
  const { handleSubmit, control, reset, getValues } = useForm();

  const handleSubmitProperties = async () => {
    const { property, propertyComparator, propertyComparatorValue } =
      getValues();
    if (!property || !propertyComparator || !propertyComparatorValue) return;

    const propertiesFilter = `${property}: ${propertyComparatorValue}: ${propertyComparator}`;
    setSelectedPlanProperties((prev) => [...prev, propertiesFilter]);
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
                {planProperties?.map((prop) => (
                  <MenuItem value={prop} key={prop}>
                    {prop}
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
                {Object.keys(comparators)?.map((key) => (
                  <MenuItem value={key} key={key}>
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
          label="Plan Properties"
          id="selectPlanProperties"
          initValue={selectedPlanProperties}
          onChange={(e) => setSelectedPlanProperties(e.target.value)}
          options={selectedPlanProperties}
        />
      </Box>
    </form>
  );
};

PlanPropertiesSelect.propTypes = {
  selectedPlanProperties: PropTypes.arrayOf(PropTypes.string).isRequired,
  setSelectedPlanProperties: PropTypes.func.isRequired,
  comparators: PropTypes.objectOf(PropTypes.string).isRequired,
};

export default PlanPropertiesSelect;
