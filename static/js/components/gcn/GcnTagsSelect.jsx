import React, { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";

import SelectWithChips from "../SelectWithChips";

import * as gcnTagsActions from "../../ducks/gcnTags";

const GcnTagsSelect = (props) => {
  const dispatch = useDispatch();

  const { selectedGcnTags, setSelectedGcnTags } = props;
  let gcnTags = [];
  gcnTags = gcnTags.concat(useSelector((state) => state.gcnTags));
  gcnTags.sort();

  useEffect(() => {
    dispatch(gcnTagsActions.fetchGcnTags());
  }, [dispatch]);

  const handleChange = (event) => setSelectedGcnTags(event.target.value);

  return (
    <div>
      {gcnTags?.length > 0 && (
        <SelectWithChips
          label="Gcn Tags"
          id="selectGcns"
          initValue={selectedGcnTags}
          onChange={handleChange}
          options={gcnTags}
        />
      )}
    </div>
  );
};

GcnTagsSelect.propTypes = {
  selectedGcnTags: PropTypes.arrayOf(PropTypes.string).isRequired,
  setSelectedGcnTags: PropTypes.func.isRequired,
};

export default GcnTagsSelect;
