import React from "react";
import { Controller, useForm } from "react-hook-form";
import { useSelector } from "react-redux";
import SelectWithChips from "./SelectWithChips";

const FilterSelect = ({ onFilterSelectChange, initValue, parent }) => {
  let filtersEnums = [];
  filtersEnums = filtersEnums.concat(
    useSelector((state) => state.enum_types.enum_types.ALLOWED_BANDPASSES)
  );
  filtersEnums.sort();
  filtersEnums.unshift("Clear selections");

  const { control } = useForm();

  return (
    <Controller
      name="filterSelect"
      control={control}
      render={({ onChange }) => (
        <SelectWithChips
          label="Filters"
          id={`filterSelect${parent}`}
          initValue={initValue}
          onChange={onFilterSelectChange}
          options={filtersEnums}
        />
      )}
    />
  );
};

export default FilterSelect;
