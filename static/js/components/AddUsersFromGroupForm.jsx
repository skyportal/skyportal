import React from "react";
import PropTypes from "prop-types";
import { useSelector, useDispatch } from "react-redux";
import Typography from "@material-ui/core/Typography";
import { useForm, Controller } from "react-hook-form";
import Autocomplete from "@material-ui/lab/Autocomplete";
import Button from "@material-ui/core/Button";
import TextField from "@material-ui/core/TextField";
import { makeStyles } from "@material-ui/core/styles";

import { showNotification } from "baselayer/components/Notifications";

import * as groupsActions from "../ducks/groups";
import FormValidationError from "./FormValidationError";

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
  const { handleSubmit, errors, reset, control, getValues } = useForm();
  const classes = useStyles();
  groups = groups?.filter((g) => g.id !== groupID) || [];

  const validateGroups = () => {
    const formState = getValues({ nest: true });
    return formState.groups.length >= 1;
  };

  const onSubmit = async (formData) => {
    const fromGroupIDs = formData.groups.map((g) => g.id);
    const result = await dispatch(
      groupsActions.addAllUsersFromGroups({ toGroupID: groupID, fromGroupIDs })
    );
    if (result.status === "success") {
      dispatch(
        showNotification("Successfully added users from specified group(s)")
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
          render={({ onChange, value, ...props }) => (
            <Autocomplete
              multiple
              id="addUsersFromGroupsSelect"
              onChange={(e, data) => onChange(data)}
              value={value}
              options={groups}
              getOptionLabel={(group) => group.name}
              filterSelectedOptions
              data-testid="addUsersFromGroupsSelect"
              renderInput={(params) => (
                <TextField
                  // eslint-disable-next-line react/jsx-props-no-spreading
                  {...params}
                  error={!!errors.groups}
                  variant="outlined"
                  label="Select Groups/Users"
                  size="small"
                  className={classes.groupSelect}
                  data-testid="addUsersFromGroupsTextField"
                />
              )}
              // eslint-disable-next-line react/jsx-props-no-spreading
              {...props}
            />
          )}
          control={control}
          rules={{ validate: validateGroups }}
          defaultValue={[]}
        />
        <div>
          <Button
            variant="contained"
            type="submit"
            name="submitAddFromGroupsButton"
            data-testid="submitAddFromGroupsButton"
            size="small"
            color="primary"
            disableElevation
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
