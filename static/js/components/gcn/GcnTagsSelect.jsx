import React, { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";

import SelectWithChips from "../SelectWithChips";

import * as gcnTagsActions from "../../ducks/gcnTags";

const GcnTagsSelect = ({
  title = "Gcn Tags",
  selectedGcnTags,
  setSelectedGcnTags,
}) => {
  const dispatch = useDispatch();
  const gcnTags = [...(useSelector((state) => state.gcnTags) || [])].sort();

  useEffect(() => {
    dispatch(gcnTagsActions.fetchGcnTags());
  }, [dispatch]);

  if (!gcnTags?.length) return null;

  const handleChange = (event) => setSelectedGcnTags(event.target.value);

  return (
    <SelectWithChips
      label={title}
      id="selectGcns"
      initValue={selectedGcnTags}
      onChange={handleChange}
      options={gcnTags}
    />
  );
};

GcnTagsSelect.propTypes = {
  title: PropTypes.string,
  selectedGcnTags: PropTypes.arrayOf(PropTypes.string).isRequired,
  setSelectedGcnTags: PropTypes.func.isRequired,
};

export default GcnTagsSelect;
