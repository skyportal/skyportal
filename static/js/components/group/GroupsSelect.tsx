import { useGetGroupsQuery } from "../../ducks/groups";

import { Group } from "../../types";
import SearchableValueSelect from "../SearchableValueSelect";

interface GroupsSelectProps {
  selectedGroups: Group[];
  setSelectedGroups: (...args: any[]) => void;
}

const GroupsSelect = (props: GroupsSelectProps) => {
  const { selectedGroups, setSelectedGroups } = props;
  const groups = useGetGroupsQuery().data?.userAccessible ?? [];

  return (
    <>
      {groups?.length > 0 && (
        <div>
          <SearchableValueSelect
            id="groups-select"
            label="Groups"
            multiple
            options={groups}
            value={selectedGroups.map((group) => group.id)}
            onChange={(ids: number[]) =>
              setSelectedGroups(
                ids.map((id) => groups.find((group) => group.id === id)),
              )
            }
            limitTags={1}
            sx={{ minWidth: "12rem" }}
          />
        </div>
      )}
    </>
  );
};

export default GroupsSelect;
