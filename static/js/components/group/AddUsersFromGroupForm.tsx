import Typography from "@mui/material/Typography";
import { Controller, useForm } from "react-hook-form";
import Autocomplete from "@mui/material/Autocomplete";
import TextField from "@mui/material/TextField";
import { makeStyles } from "tss-react/mui";
import { showNotification } from "baselayer/components/Notifications";

import { useAppDispatch, useAppSelector } from "../../types/hooks";
import { Group } from "../../types";
import * as groupsActions from "../../ducks/groups";
import FormValidationError from "../FormValidationError";
import Button from "../Button";

const useStyles = makeStyles()(() => ({
  groupSelect: {
    width: "20rem",
    marginBottom: "0.75rem",
  },
  heading: {
    fontSize: "1.0625rem",
    fontWeight: 500,
  },
}));

interface AddUsersFromGroupFormProps {
  groupID: number;
}

const AddUsersFromGroupForm = ({ groupID }: AddUsersFromGroupFormProps) => {
  const dispatch = useAppDispatch();
  let { all: groups } = useAppSelector((state) => state.groups);
  const {
    handleSubmit,
    reset,
    control,
    getValues,

    formState: { errors },
  } = useForm();
  const { classes } = useStyles();
  groups = groups?.filter((g) => g.id !== groupID) || [];

  const validateGroups = () => {
    const formState = getValues();
    return formState["groups"].length >= 1;
  };

  const onSubmit = async (formData: any) => {
    const fromGroupIDs = formData.groups?.map((g: Group) => g.id);
    const result: any = await dispatch(
      groupsActions.addAllUsersFromGroups({ toGroupID: groupID, fromGroupIDs }),
    );
    if (result.status === "success") {
      dispatch(
        showNotification("Successfully added users from specified group(s)"),
      );
      reset({ groups: [] });
    }
  };

  return (
    <div>
      <Typography className={classes.heading}>
        Add all users from other group(s)
      </Typography>
      <form onSubmit={handleSubmit(onSubmit)}>
        {!!errors["groups"] && (
          <FormValidationError message="Please select at least one group/user" />
        )}
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
              data-testid="addUsersFromGroupsSelect"
              renderInput={(field) => (
                <TextField
                  {...field}
                  error={!!errors["groups"]}
                  variant="outlined"
                  label="Select Groups/Users"
                  size="small"
                  className={classes.groupSelect}
                  data-testid="addUsersFromGroupsTextField"
                />
              )}
            />
          )}
          control={control}
          rules={{ validate: validateGroups }}
          defaultValue={[]}
        />
        <div>
          <Button
            primary
            type="submit"
            name="submitAddFromGroupsButton"
            data-testid="submitAddFromGroupsButton"
            size="small"
          >
            Add users
          </Button>
        </div>
      </form>
    </div>
  );
};

export default AddUsersFromGroupForm;
