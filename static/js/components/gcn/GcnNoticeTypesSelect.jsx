import React from "react";
import { useSelector } from "react-redux";
import PropTypes from "prop-types";

import SelectWithChips from "../SelectWithChips";

const GcnNoticeTypesSelect = (props) => {
  const { selectedGcnNoticeTypes, setSelectedGcnNoticeTypes } = props;
  const gcn_notice_types = useSelector((state) => state.config.gcnNoticeTypes);

  const handleChange = (event) => setSelectedGcnNoticeTypes(event.target.value);

  return (
    <div>
      {gcn_notice_types?.length > 0 && (
        <SelectWithChips
          label="Gcn Notice Types"
          id="selectGcns"
          initValue={selectedGcnNoticeTypes}
          onChange={handleChange}
          options={gcn_notice_types}
        />
      )}
    </div>
  );
};

GcnNoticeTypesSelect.propTypes = {
  selectedGcnNoticeTypes: PropTypes.arrayOf(PropTypes.string).isRequired,
  setSelectedGcnNoticeTypes: PropTypes.func.isRequired,
};

export default GcnNoticeTypesSelect;
