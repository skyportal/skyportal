import SelectWithChips from "../../SelectWithChips";

interface OriginSelectProps {
  onOriginSelectChange: (...args: any[]) => void;
  initValue?: string[];
  parent: string;
}

const OriginSelect = ({
  onOriginSelectChange,
  initValue = [],
  parent,
}: OriginSelectProps) => {
  const originsList = ["Clear selections"]?.filter(
    (origin) => origin !== "None",
  );

  return (
    <>
      {originsList && (
        <SelectWithChips
          label="Origin"
          id={`originSelect${parent}`}
          initValue={initValue}
          onChange={onOriginSelectChange}
          options={originsList}
        />
      )}
    </>
  );
};

export default OriginSelect;
