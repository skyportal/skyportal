import SelectWithChips from "../SelectWithChips";

import { useGetGcnTagsQuery } from "../../ducks/gcnTags";

interface GcnTagsSelectProps {
  title?: string;
  selectedGcnTags: string[];
  setSelectedGcnTags: (...args: any[]) => void;
  /** Offer only the tags events of this messenger have carried. */
  detectorType?: string;
}

const GcnTagsSelect = ({
  title = "Gcn Tags",
  selectedGcnTags,
  setSelectedGcnTags,
  detectorType,
}: GcnTagsSelectProps) => {
  const { data: gcnTagsData } = useGetGcnTagsQuery(
    detectorType ? { detectorType } : undefined,
  );
  const gcnTags = [...(gcnTagsData || [])].sort();

  if (!gcnTags?.length) return null;

  const handleChange = (event: any) => setSelectedGcnTags(event.target.value);

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

export default GcnTagsSelect;
