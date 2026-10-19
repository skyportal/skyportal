import PropertiesSelect from "../PropertiesSelect";

import { useGetGcnPropertiesQuery } from "../../ducks/gcnProperties";

interface GcnPropertiesSelectProps {
  selectedGcnProperties: string[];
  setSelectedGcnProperties: (...args: any[]) => void;
  conversions: Record<string, any>;
  comparators: Record<string, string>;
}

const GcnPropertiesSelect = ({
  selectedGcnProperties,
  setSelectedGcnProperties,
  conversions,
  comparators,
}: GcnPropertiesSelectProps) => {
  const { data: gcnPropertiesData } = useGetGcnPropertiesQuery();
  const gcnProperties = (
    [...(gcnPropertiesData || [])] as unknown as string[]
  ).sort();

  return (
    <PropertiesSelect
      label="Gcn Properties"
      id="selectGcnProperties"
      properties={gcnProperties}
      selected={selectedGcnProperties}
      setSelected={setSelectedGcnProperties}
      comparators={comparators}
      conversions={conversions}
      valueDefault="0.0"
    />
  );
};

export default GcnPropertiesSelect;
