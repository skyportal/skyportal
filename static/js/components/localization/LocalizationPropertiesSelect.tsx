import PropertiesSelect from "../PropertiesSelect";

import { useGetLocalizationPropertiesQuery } from "../../ducks/localizationProperties";

interface LocalizationPropertiesSelectProps {
  selectedLocalizationProperties: string[];
  setSelectedLocalizationProperties: (...args: any[]) => void;
  comparators: Record<string, string>;
}

const LocalizationPropertiesSelect = ({
  selectedLocalizationProperties,
  setSelectedLocalizationProperties,
  comparators,
}: LocalizationPropertiesSelectProps) => {
  const { data: localizationPropertiesData } =
    useGetLocalizationPropertiesQuery(undefined);
  const localizationProperties = (
    [...(localizationPropertiesData || [])] as unknown as string[]
  ).sort();

  return (
    <PropertiesSelect
      label="Localization Properties"
      id="selectLocalizations"
      properties={localizationProperties}
      selected={selectedLocalizationProperties}
      setSelected={setSelectedLocalizationProperties}
      comparators={comparators}
      valueDefault="0.0"
    />
  );
};

export default LocalizationPropertiesSelect;
