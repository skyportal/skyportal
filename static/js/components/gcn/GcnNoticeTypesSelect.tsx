import SelectWithChips from "../SelectWithChips";

import { useGetConfigQuery } from "../../ducks/config";

interface GcnNoticeTypesSelectProps {
  selectedGcnNoticeTypes: string[];
  setSelectedGcnNoticeTypes: (value: any) => void;
}

const GcnNoticeTypesSelect = ({
  selectedGcnNoticeTypes,
  setSelectedGcnNoticeTypes,
}: GcnNoticeTypesSelectProps) => {
  const gcn_notice_types = (useGetConfigQuery().data as any)?.gcnNoticeTypes;
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
