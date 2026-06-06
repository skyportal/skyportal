import SelectWithChips from "../../SelectWithChips";
import { useGetEnumTypesQuery } from "../../../ducks/enum_types";

interface FilterSelectProps {
  onFilterSelectChange: (...args: any[]) => void;
  initValue?: string[];
  parent: string;
}

const FilterSelect = ({
  onFilterSelectChange,
  initValue = [],
  parent,
}: FilterSelectProps) => {
  const { data: enum_types } = useGetEnumTypesQuery();
  let filtersEnums: string[] = [];
  filtersEnums = filtersEnums.concat(enum_types?.["ALLOWED_BANDPASSES"] ?? []);
  filtersEnums.sort();
  filtersEnums.unshift("Clear selections");

  return (
    <SelectWithChips
      label="Filters"
      id={`filterSelect${parent}`}
      initValue={initValue}
      onChange={onFilterSelectChange}
      options={filtersEnums}
    />
  );
};

export default FilterSelect;
