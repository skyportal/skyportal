import React, { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
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

import * as localizationPropertiesActions from "../../ducks/localizationProperties";

const LocalizationPropertiesSelect = ({
  selectedLocalizationProperties,
  setSelectedLocalizationProperties,
  comparators,
}) => {
  const dispatch = useDispatch();
  const localizationProperties = [
    ...(useSelector((state) => state.localizationProperties) || []),
  ].sort();
  const { handleSubmit, control, reset, getValues } = useForm();

  useEffect(() => {
    dispatch(localizationPropertiesActions.fetchLocalizationProperties());
  }, [dispatch]);

  const handleSubmitProperties = async () => {
    const { property, propertyComparator, propertyComparatorValue } =
      getValues();
    if (!property || !propertyComparator || !propertyComparatorValue) return;

    const propertiesFilter = `${property}: ${propertyComparatorValue}: ${propertyComparator}`;
    setSelectedLocalizationProperties((prev) => [...prev, propertiesFilter]);
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
                {localizationProperties?.map((prop) => (
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
          label="Localization Properties"
          id="selectLocalizations"
          initValue={selectedLocalizationProperties}
          onChange={(e) => setSelectedLocalizationProperties(e.target.value)}
          options={selectedLocalizationProperties}
        />
      </Box>
    </form>
  );
};

LocalizationPropertiesSelect.propTypes = {
  selectedLocalizationProperties: PropTypes.arrayOf(PropTypes.string)
    .isRequired,
  setSelectedLocalizationProperties: PropTypes.func.isRequired,
  comparators: PropTypes.objectOf(PropTypes.string).isRequired,
};

export default LocalizationPropertiesSelect;
