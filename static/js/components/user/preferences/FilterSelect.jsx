import React from "react";
import PropTypes from "prop-types";
import { useSelector } from "react-redux";
import SelectWithChips from "../../SelectWithChips";

const FilterSelect = ({ onFilterSelectChange, initValue, parent }) => {
  let filtersEnums = [];
  filtersEnums = filtersEnums.concat(
    useSelector((state) => state.enum_types.enum_types.ALLOWED_BANDPASSES),
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

FilterSelect.propTypes = {
  onFilterSelectChange: PropTypes.func.isRequired,
  initValue: PropTypes.arrayOf(PropTypes.string),
  parent: PropTypes.string.isRequired,
};

FilterSelect.defaultProps = {
  initValue: [],
};

export default FilterSelect;
