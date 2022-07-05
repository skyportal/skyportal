import React, { useEffect } from "react";
import PropTypes from "prop-types";
import { useSelector, useDispatch } from "react-redux";
import SelectWithChips from "./SelectWithChips";

import * as photometryActions from "../ducks/photometry";

const OriginSelect = ({ onOriginSelectChange, initValue, parent }) => {
  const dispatch = useDispatch();

  useEffect(() => {
    const fetchOrigins = async () => {
      await dispatch(photometryActions.fetchAllOrigins());
    };
    fetchOrigins();
  }, [dispatch]);

  const originsList = ["Clear selections"].concat(
    useSelector((state) => state.photometry.origins)?.filter(
      (origin) => origin !== "None"
    )
  );

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
