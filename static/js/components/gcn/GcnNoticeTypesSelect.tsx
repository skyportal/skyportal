import React from "react";

import SelectWithChips from "../SelectWithChips";
import { useAppSelector } from "../../types/hooks";

interface GcnNoticeTypesSelectProps {
  selectedGcnNoticeTypes: string[];
  setSelectedGcnNoticeTypes: (value: any) => void;
}

const GcnNoticeTypesSelect = ({
  selectedGcnNoticeTypes,
  setSelectedGcnNoticeTypes,
}: GcnNoticeTypesSelectProps) => {
  const gcn_notice_types = useAppSelector(
    (state) => state.config.gcnNoticeTypes,
  );
  if (!gcn_notice_types?.length) return null;

  return (
    <SelectWithChips
      label="Gcn Notice Types"
      id="selectGcns"
      initValue={selectedGcnNoticeTypes}
      onChange={(e: any) => setSelectedGcnNoticeTypes(e.target.value)}
      options={gcn_notice_types}
    />
  );
};

export default GcnNoticeTypesSelect;
