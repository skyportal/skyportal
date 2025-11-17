import React from "react";
import { useSelector } from "react-redux";
import PropTypes from "prop-types";

import SelectWithChips from "../SelectWithChips";

const GcnNoticeTypesSelect = ({
  selectedGcnNoticeTypes,
  setSelectedGcnNoticeTypes,
}) => {
  const gcn_notice_types = useSelector((state) => state.config.gcnNoticeTypes);
  if (!gcn_notice_types?.length) return null;

  return (
    <SelectWithChips
      label="Gcn Notice Types"
      id="selectGcns"
      initValue={selectedGcnNoticeTypes}
      onChange={(e) => setSelectedGcnNoticeTypes(e.target.value)}
      options={gcn_notice_types}
    />
  );
};

GcnNoticeTypesSelect.propTypes = {
  selectedGcnNoticeTypes: PropTypes.arrayOf(PropTypes.string).isRequired,
  setSelectedGcnNoticeTypes: PropTypes.func.isRequired,
};

export default GcnNoticeTypesSelect;
