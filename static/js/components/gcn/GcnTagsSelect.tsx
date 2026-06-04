import { useEffect } from "react";
import { useAppDispatch, useAppSelector } from "../../types/hooks";

import SelectWithChips from "../SelectWithChips";

import * as gcnTagsActions from "../../ducks/gcnTags";

interface GcnTagsSelectProps {
  title?: string;
  selectedGcnTags: string[];
  setSelectedGcnTags: (...args: any[]) => void;
}

const GcnTagsSelect = ({
  title = "Gcn Tags",
  selectedGcnTags,
  setSelectedGcnTags,
}: GcnTagsSelectProps) => {
  const dispatch = useAppDispatch();
  const gcnTags = [
    ...(useAppSelector((state) => state["gcnTags"]) || []),
  ].sort();

  useEffect(() => {
    dispatch(gcnTagsActions.fetchGcnTags());
  }, [dispatch]);

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
