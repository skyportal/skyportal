import React, { useEffect } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import SelectWithChips from "./SelectWithChips";

// import * as photometryActions from "../ducks/photometry";

const OriginSelect = ({ onOriginSelectChange, initValue, parent }) => {
  const dispatch = useDispatch();
  const photometry = useSelector((state) => state.photometry);

  useEffect(() => {
    // const fetchOrigins = async () => {
    //   await dispatch(photometryActions.fetchAllOrigins());
    // };
    // fetchOrigins(); //TODO: uncomment this line when the API is fixed. For now this times out.
  }, [dispatch]);

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
