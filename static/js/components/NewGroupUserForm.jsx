import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import TextField from "@material-ui/core/TextField";
import Autocomplete, {
  createFilterOptions,
} from "@material-ui/lab/Autocomplete";
import Button from "@material-ui/core/Button";
import Typography from "@material-ui/core/Typography";
import CircularProgress from "@material-ui/core/CircularProgress";
import { makeStyles } from "@material-ui/core/styles";

import * as groupsActions from "../ducks/groups";
import * as usersActions from "../ducks/users";

const filter = createFilterOptions();

const useStyles = makeStyles(() => ({
  heading: {
    fontSize: "1.0625rem",
    fontWeight: 500,
  },
}));

const NewGroupUserForm = ({ group_id }) => {
  const dispatch = useDispatch();
  const { users: allUsers } = useSelector((state) => state.users);
  const [formState, setFormState] = useState({
    userID: null,
    admin: false,
  });
  const classes = useStyles();

  useEffect(() => {
    if (allUsers.length === 0) {
      dispatch(usersActions.fetchUsers());
    }
  }, [dispatch, allUsers]);

  const handleClickSubmit = async () => {
    const result = await dispatch(
      groupsActions.addGroupUser({
        userID: formState.userID,
        admin: formState.admin,
        group_id,
      })
    );
    if (result.status === "success") {
      setFormState({
        userID: null,
        admin: false,
      });
    }
  };

  const toggleAdmin = (event) => {
    setFormState({
      ...formState,
      admin: event.target.checked,
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
        id="newGroupUserInput"
        value={
          allUsers.filter((user) => user.id === formState.userID)[0] || null
        }
        onChange={(event, newValue) => {
          setFormState({ userID: newValue?.id });
        }}
        filterOptions={(options, params) => {
          const filtered = filter(options, params);
          return filtered;
        }}
        selectOnFocus
        clearOnBlur
        handleHomeEndKeys
        options={allUsers}
        getOptionLabel={(option) => option.username}
        renderOption={(option) => option.username}
        style={{ width: 300, paddingBottom: 10 }}
        defaultValue={null}
        renderInput={(params) => (
          // eslint-disable-next-line react/jsx-props-no-spreading
          <TextField {...params} label="Username" />
        )}
      />
      <input
        type="checkbox"
        checked={formState.admin || false}
        onChange={toggleAdmin}
      />
      Group Admin &nbsp;&nbsp;
      <Button
        onClick={handleClickSubmit}
        variant="contained"
        size="small"
        disableElevation
      >
        Add user to group
      </Button>
    </div>
  );
};
NewGroupUserForm.propTypes = {
  group_id: PropTypes.number.isRequired,
};

export default NewGroupUserForm;
