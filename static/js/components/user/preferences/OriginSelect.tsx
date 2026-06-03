import { useAppSelector } from "../../../types/hooks";
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
  const photometry = useAppSelector((state) => state.photometry);

  const originsList = ["Clear selections"]
    .concat(photometry?.origins || [])
    ?.filter((origin) => origin !== "None");

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
