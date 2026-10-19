import PropertiesSelect from "../PropertiesSelect";

const PLAN_PROPERTIES = [
  "area",
  "num_observations",
  "probability",
  "tot_time_with_overhead",
  "total_time",
];

interface PlanPropertiesSelectProps {
  selectedPlanProperties: string[];
  setSelectedPlanProperties: (...args: any[]) => void;
  comparators: Record<string, string>;
}

const PlanPropertiesSelect = ({
  selectedPlanProperties,
  setSelectedPlanProperties,
  comparators,
}: PlanPropertiesSelectProps) => (
  <PropertiesSelect
    label="Plan Properties"
    id="selectPlanProperties"
    properties={PLAN_PROPERTIES}
    selected={selectedPlanProperties}
    setSelected={setSelectedPlanProperties}
    comparators={comparators}
  />
);

export default PlanPropertiesSelect;
