import { UnifiedBuilderProvider } from "../../../contexts/UnifiedBuilderContext";
import FilterBuilderContent from "./FilterBuilderContent";

const FilterBuilder = () => {
  return (
    <UnifiedBuilderProvider mode="filter">
      <FilterBuilderContent />
    </UnifiedBuilderProvider>
  );
};

export default FilterBuilder;
