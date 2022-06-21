import React, { useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import PropTypes from "prop-types";

import SelectWithChips from "./SelectWithChips";
import { fetchGcnNoticeTypes } from "../ducks/gcnNoticeTypes";

const GcnNoticeTypesSelect = (props) => {
  const { selectedGcnNoticeTypes, setSelectedGcnNoticeTypes } = props;
  const dispatch = useDispatch();
  const gcn_notice_types = useSelector(
    (state) => state.gcnNoticeTypes.gcnNoticeTypes
  );

  useEffect(() => {
    dispatch(fetchGcnNoticeTypes());
  }, []);

  const handleChange = (event) => setSelectedGcnNoticeTypes(event.target.value);

  return (
    <div>
      {gcn_notice_types?.length > 0 && (
        <div style={{ marginBottom: "1rem" }}>
          <SelectWithChips
            label="Gcn Notice Types"
            id="selectGcns"
            initValue={selectedGcnNoticeTypes}
            onChange={handleChange}
            options={gcn_notice_types}
          />
        </div>
      )}
    </div>
  );
};

GcnNoticeTypesSelect.propTypes = {
  selectedGcnNoticeTypes: PropTypes.arrayOf(PropTypes.string).isRequired,
  setSelectedGcnNoticeTypes: PropTypes.func.isRequired,
};

export default GcnNoticeTypesSelect;
