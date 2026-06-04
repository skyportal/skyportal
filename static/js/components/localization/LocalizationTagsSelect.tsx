import { useEffect } from "react";

import SelectWithChips from "../SelectWithChips";

import * as localizationTagsActions from "../../ducks/localizationTags";
import { useAppDispatch, useAppSelector } from "../../types/hooks";

interface LocalizationTagsSelectProps {
  title?: string;
  selectedLocalizationTags: string[];
  setSelectedLocalizationTags: (value: any) => void;
}

const LocalizationTagsSelect = ({
  title = "Localization Tags",
  selectedLocalizationTags,
  setSelectedLocalizationTags,
}: LocalizationTagsSelectProps) => {
  const dispatch = useAppDispatch();
  const localizationTags = [
    ...(useAppSelector((state) => state["localizationTags"]) || []),
  ].sort();

  useEffect(() => {
    dispatch(localizationTagsActions.fetchLocalizationTags());
  }, [dispatch]);

  if (!localizationTags?.length) return null;

  return (
    <SelectWithChips
      label={title}
      id="selectLocalizations"
      initValue={selectedLocalizationTags}
      onChange={(e: any) => setSelectedLocalizationTags(e.target.value)}
      options={localizationTags}
    />
  );
};

export default LocalizationTagsSelect;
