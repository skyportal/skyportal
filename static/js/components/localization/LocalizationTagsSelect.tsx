import SelectWithChips from "../SelectWithChips";

import { useGetLocalizationTagsQuery } from "../../ducks/localizationTags";

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
  const { data } = useGetLocalizationTagsQuery();
  const localizationTags = [...(data || [])].sort();

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
