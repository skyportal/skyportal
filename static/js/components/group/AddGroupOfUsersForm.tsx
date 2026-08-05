import Typography from "@mui/material/Typography";
import { Controller, useForm } from "react-hook-form";
import Autocomplete from "@mui/material/Autocomplete";
import TextField from "@mui/material/TextField";
import Box from "@mui/material/Box";
import { showNotification } from "baselayer/components/Notifications";

import { useAppDispatch } from "../../types/hooks";
import { Group } from "../../types";
import {
  useAddAllUsersFromGroupsMutation,
  useGetGroupsQuery,
} from "../../ducks/groups";
import FormValidationError from "../FormValidationError";
import Button from "../Button";

interface AddGroupOfUsersFormProps {
  groupID: number;
}

const AddGroupOfUsersForm = ({ groupID }: AddGroupOfUsersFormProps) => {
  const dispatch = useAppDispatch();
  let groups = useGetGroupsQuery().data?.all ?? null;
  const [addAllUsersFromGroups] = useAddAllUsersFromGroupsMutation();
  const {
    handleSubmit,
    reset,
    control,
    getValues,

    formState: { errors },
  } = useForm();
  groups =
    groups?.filter((g) => g.id !== groupID && !g["single_user_group"]) || [];

  const validateGroups = () => {
    const formState = getValues();
    return formState["groups"].length >= 1;
  };

  const onSubmit = async (formData: any) => {
    const fromGroupIDs = formData.groups?.map((g: Group) => g.id);
    try {
      await addAllUsersFromGroups({
        toGroupID: groupID,
        fromGroupIDs,
      }).unwrap();
      dispatch(
        showNotification("Successfully added users from specified group(s)"),
      );
      reset({ groups: [] });
    } catch {
      // error notification handled by the API layer
    }
  };

  return (
    <Box sx={{ width: "100%" }}>
      <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
        Add all members of the selected group(s) to this group
      </Typography>
      <form onSubmit={handleSubmit(onSubmit)}>
        {!!errors["groups"] && (
          <FormValidationError message="Please select at least one group/user" />
        )}
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            flexWrap: "wrap",
            gap: 2,
          }}
        >
          <Controller
            name="groups"
            render={({ field: { onChange, value } }) => (
              <Autocomplete
                multiple
                id="addUsersFromGroupsSelect"
                onChange={(_e, data) => onChange(data)}
                value={value}
                options={groups}
                getOptionLabel={(group: Group) => group.name}
                filterSelectedOptions
                sx={{ width: 300 }}
                renderInput={(field) => (
                  <TextField
                    {...field}
                    error={!!errors["groups"]}
                    label="Select Groups/Users"
                    data-testid="addUsersFromGroupsTextField"
                  />
                )}
              />
            )}
            control={control}
            rules={{ validate: validateGroups }}
            defaultValue={[]}
          />
        </Box>
        <Button
          secondary
          type="submit"
          name="submitAddFromGroupsButton"
          data-testid="submitAddFromGroupsButton"
          sx={{ mt: 2 }}
        >
          Add users
        </Button>
      </form>
    </Box>
  );
};

export default AddGroupOfUsersForm;
