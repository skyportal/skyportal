import { Controller, useForm } from "react-hook-form";
import { showNotification } from "baselayer/components/Notifications";

import { useAppDispatch } from "../../types/hooks";
import { Group } from "../../types";
import {
  useAddAllUsersFromGroupsMutation,
  useGetGroupsQuery,
} from "../../ducks/groups";
import SearchableSelect from "../SearchableSelect";
import type { AddMembersFormProps } from "./GroupAddMembers";

const AddGroupOfUsersForm = ({
  groupID,
  formId,
  onSuccess,
}: AddMembersFormProps) => {
  const dispatch = useAppDispatch();
  const groups = (useGetGroupsQuery().data?.all ?? []).filter(
    (group) => group.id !== groupID && !group["single_user_group"],
  );
  const [addAllUsersFromGroups] = useAddAllUsersFromGroupsMutation();
  const {
    handleSubmit,
    control,
    formState: { errors },
  } = useForm({ defaultValues: { groups: [] as Group[] } });

  const onSubmit = async ({ groups: selected }: { groups: Group[] }) => {
    const { error } = await addAllUsersFromGroups({
      toGroupID: groupID,
      fromGroupIDs: selected.map((group) => group.id),
    });
    if (error) return;
    dispatch(
      showNotification("Successfully added users from specified group(s)"),
    );
    onSuccess();
  };

  return (
    <form id={formId} onSubmit={handleSubmit(onSubmit)}>
      <Controller
        name="groups"
        control={control}
        rules={{ validate: (value) => value.length > 0 }}
        render={({ field: { onChange, value } }) => (
          <SearchableSelect
            multiple
            id="addUsersFromGroupsSelect"
            label="Groups"
            value={value}
            onChange={(_event, data) => onChange(data)}
            options={groups}
            getOptionLabel={(group: Group) => group.name}
            filterSelectedOptions
            fullWidth
            error={!!errors.groups}
            helperText={
              errors.groups
                ? "Please select at least one group"
                : "All their members are added to this group"
            }
            textFieldProps={{ "data-testid": "addUsersFromGroupsTextField" }}
            sx={{ mt: 1 }}
          />
        )}
      />
    </form>
  );
};

export default AddGroupOfUsersForm;
