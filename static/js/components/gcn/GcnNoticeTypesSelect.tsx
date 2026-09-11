import SelectWithChips from "../SelectWithChips";

import { useGetConfigQuery } from "../../ducks/config";

interface GcnNoticeTypesSelectProps {
  selectedGcnNoticeTypes: string[];
  setSelectedGcnNoticeTypes: (value: any) => void;
  // Set when the same picker is reused to choose notice types to exclude.
  label?: string;
  id?: string;
}

const GcnNoticeTypesSelect = ({
  selectedGcnNoticeTypes,
  setSelectedGcnNoticeTypes,
  label = "Gcn Notice Types",
  id = "selectGcnNoticeTypes",
}: GcnNoticeTypesSelectProps) => {
  const gcn_notice_types = (useGetConfigQuery().data as any)?.gcnNoticeTypes;
  if (!gcn_notice_types?.length) return null;

  return (
    <SelectWithChips
      label={label}
      id={id}
      initValue={selectedGcnNoticeTypes}
      onChange={(e: any) => setSelectedGcnNoticeTypes(e.target.value)}
      options={gcn_notice_types}
    />
  );
};

export default GcnNoticeTypesSelect;
