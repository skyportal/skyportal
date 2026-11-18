import { Group } from "../../types";
import SearchableValueSelect from "../SearchableValueSelect";

interface GroupShareSelectProps {
  groupList: Group[];
  groupIDs: number[];
  setGroupIDs: (...args: any[]) => void;
  maxGroups?: number;
}

const GroupShareSelect = ({
  groupList,
  groupIDs,
  setGroupIDs,
  maxGroups = 2,
}: GroupShareSelectProps) => (
  <SearchableValueSelect
    id="selectGroups"
    label="Share Data With"
    multiple
    options={groupList ?? []}
    value={groupIDs}
    onChange={setGroupIDs}
    limitTags={maxGroups}
    renderOptionContent={(group) => (
      <div data-testid={`group_${group.id}`}>{group.name}</div>
    )}
    sx={{ minWidth: 220, mt: 1 }}
  />
);

export default GroupShareSelect;
