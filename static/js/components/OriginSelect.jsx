import React from "react";
import { Controller, useForm } from "react-hook-form";
import SelectWithChips from "./SelectWithChips";

const OriginSelect = ({ onOriginSelectChange, initValue, parent }) => {
  const origins = ["Clear selections", "Muphoten", "STDpipe"];

  const { control } = useForm();

  return (
    <Controller
      name="originSelect"
      control={control}
      render={({ onChange }) => (
        <SelectWithChips
          label="Origin"
          id={`originSelect${parent}`}
          initValue={initValue}
          onChange={onOriginSelectChange}
          options={origins}
        />
      )}
    />
  );
};

export default OriginSelect;
