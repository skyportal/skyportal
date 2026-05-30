import React, { useEffect, useState } from "react";
import TextField from "@mui/material/TextField";
import Autocomplete, { createFilterOptions } from "@mui/material/Autocomplete";
import Typography from "@mui/material/Typography";
import CircularProgress from "@mui/material/CircularProgress";
import { makeStyles } from "tss-react/mui";
import { showNotification } from "baselayer/components/Notifications";

import { useAppSelector, useAppDispatch } from "../../types/hooks";
import * as groupsActions from "../../ducks/groups";
import * as usersActions from "../../ducks/users";
import Button from "../Button";

const filter = createFilterOptions<any>();

const useStyles = makeStyles()(() => ({
  heading: {
    fontSize: "1.0625rem",
    fontWeight: 500,
  },
}));

interface FormState {
  userID: number | null;
  admin: boolean;
  canSave: boolean;
}

const defaultState: FormState = {
  userID: null,
  admin: false,
  canSave: true,
};

interface NewGroupUserFormProps {
  group_id: number;
}

const NewGroupUserForm = ({ group_id }: NewGroupUserFormProps) => {
  const dispatch = useAppDispatch();
  const { users: allUsers } = useAppSelector((state) => state.users);
  const [formState, setFormState] = useState<FormState>(defaultState);
  const { classes } = useStyles();

  useEffect(() => {
    if (allUsers.length === 0) {
      dispatch(usersActions.fetchUsers());
    }
  }, [dispatch, allUsers]);

  const handleClickSubmit = async () => {
    if (!formState.userID) {
      dispatch(showNotification("Please select a user", "error"));
    } else {
      const result = (await dispatch(
        groupsActions.addGroupUser({
          group_id,
          ...formState,
        } as any),
      )) as any;
      if (result.status === "success") {
        setFormState(defaultState);
      }
    }
  };

  const toggleCheckbox = (event: any) => {
    setFormState({
      ...formState,
      [event.target.name]: event.target.checked,
    });
  };

  if (!allUsers?.length) {
    return <CircularProgress />;
  }

  return (
    <div>
      <Typography className={classes.heading}>
        Add an existing user to this group
      </Typography>
      <Autocomplete
        data-testid="newGroupUser"
        onChange={(event: any, newValue: any) =>
          setFormState({ userID: newValue?.id } as any)
        }
        filterOptions={(options, params) => {
          const filtered = filter(options, params);
          return filtered;
        }}
        selectOnFocus
        clearOnBlur
        handleHomeEndKeys
        options={allUsers}
        getOptionLabel={(option: any) => option.username}
        sx={{ width: 300, paddingBottom: 10 }}
        defaultValue={null}
        renderInput={(params) => (
          <TextField
            {...params}
            label="Username"
            data-testid="newGroupUserTextInput"
          />
        )}
      />
      <input
        type="checkbox"
        checked={formState.canSave}
        onChange={toggleCheckbox}
        name="canSave"
        data-testid="canSaveCheckbox"
      />
      Can save to this group &nbsp;&nbsp;
      <input
        type="checkbox"
        checked={formState.admin}
        onChange={toggleCheckbox}
        name="admin"
        data-testid="adminCheckbox"
      />
      Group Admin &nbsp;&nbsp;
      <Button primary onClick={handleClickSubmit} size="small">
        Add user to group
      </Button>
    </div>
  );
};

export default NewGroupUserForm;
