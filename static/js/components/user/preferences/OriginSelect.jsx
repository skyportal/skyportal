import React from "react";
import PropTypes from "prop-types";
import { useSelector } from "react-redux";
import SelectWithChips from "../../SelectWithChips";

const OriginSelect = ({ onOriginSelectChange, initValue, parent }) => {
  const photometry = useSelector((state) => state.photometry);

  const originsList = ["Clear selections"]
    .concat(photometry?.origins || [])
    ?.filter((origin) => origin !== "None");

  return (
    <>
      {originsList && (
        <SelectWithChips
          label="Origin"
          id={`originSelect${parent}`}
          initValue={initValue}
          onChange={onOriginSelectChange}
          options={originsList}
        />
      )}
    </>
  );
};

OriginSelect.propTypes = {
  onOriginSelectChange: PropTypes.func.isRequired,
  initValue: PropTypes.arrayOf(PropTypes.string),
  parent: PropTypes.string.isRequired,
};

OriginSelect.defaultProps = {
  initValue: [],
};

export default OriginSelect;
