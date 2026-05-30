import React from "react";
import { useAppSelector } from "../../../types/hooks";
import SelectWithChips from "../../SelectWithChips";

interface FilterSelectProps {
  onFilterSelectChange: (...args: any[]) => void;
  initValue?: string[];
  parent: string;
}

const FilterSelect = ({
  onFilterSelectChange,
  initValue = [],
  parent,
}: FilterSelectProps) => {
  let filtersEnums: string[] = [];
  filtersEnums = filtersEnums.concat(
    useAppSelector((state) => state.enum_types.enum_types.ALLOWED_BANDPASSES),
  );
  filtersEnums.sort();
  filtersEnums.unshift("Clear selections");

  return (
    <SelectWithChips
      label="Filters"
      id={`filterSelect${parent}`}
      initValue={initValue}
      onChange={onFilterSelectChange}
      options={filtersEnums}
    />
  );
};

export default FilterSelect;
