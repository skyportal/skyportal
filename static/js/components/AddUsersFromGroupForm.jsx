import React from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import Typography from "@mui/material/Typography";
import { Controller, useForm } from "react-hook-form";
import Autocomplete from "@mui/material/Autocomplete";
import TextField from "@mui/material/TextField";
import makeStyles from "@mui/styles/makeStyles";

import { showNotification } from "baselayer/components/Notifications";

import * as groupsActions from "../ducks/groups";
import FormValidationError from "./FormValidationError";
import Button from "./Button";

const useStyles = makeStyles(() => ({
  groupSelect: {
    width: "20rem",
    marginBottom: "0.75rem",
  },
  heading: {
    fontSize: "1.0625rem",
    fontWeight: 500,
  },
}));

const AddUsersFromGroupForm = ({ groupID }) => {
  const dispatch = useDispatch();
  let { all: groups } = useSelector((state) => state.groups);
  const {
    handleSubmit,
    reset,
    control,
    getValues,

    formState: { errors },
  } = useForm();
  const classes = useStyles();
  groups = groups?.filter((g) => g.id !== groupID) || [];

  const validateGroups = () => {
    const formState = getValues();
    return formState.groups.length >= 1;
  };

  const onSubmit = async (formData) => {
    const fromGroupIDs = formData.groups?.map((g) => g.id);
    const result = await dispatch(
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
        {!!errors.groups && (
          <FormValidationError message="Please select at least one group/user" />
        )}
        <Controller
          name="groups"
          render={({ field: { onChange, value } }) => (
            <Autocomplete
              multiple
              id="addUsersFromGroupsSelect"
              onChange={(e, data) => onChange(data)}
              value={value}
              options={groups}
              getOptionLabel={(group) => group.name}
              filterSelectedOptions
              data-testid="addUsersFromGroupsSelect"
              renderInput={(field) => (
                <TextField
                  // eslint-disable-next-line react/jsx-props-no-spreading
                  {...field}
                  error={!!errors.groups}
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
AddUsersFromGroupForm.propTypes = {
  groupID: PropTypes.number.isRequired,
};

export default AddUsersFromGroupForm;
