import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { useDispatch, useSelector } from 'react-redux';
import TextField from '@material-ui/core/TextField';
import Autocomplete, { createFilterOptions } from '@material-ui/lab/Autocomplete';

import * as Action from '../ducks/groups';

const filter = createFilterOptions();

const NewGroupUserForm = ({ group_id }) => {
  const dispatch = useDispatch();
  const { allUsers } = useSelector((state) => state.users);
  const [formState, setFormState] = useState({
    newUserEmail: null,
    admin: false
  });

  const handleSubmit = (event) => {
    event.preventDefault();
    dispatch(Action.addGroupUser({
      username: formState.newUserEmail,
      admin: formState.admin,
      group_id
    }));
    setFormState({
      newUserEmail: null,
      admin: false
    });
  };

  const toggleAdmin = (event) => {
    setFormState({
      ...formState,
      admin: event.target.checked
    });
  };

  return (
    <div>
      <Autocomplete
        id="newUserEmail"
        value={formState.newUserEmail}
        onChange={(event, newValue) => {
          if (typeof newValue === 'string') {
            setFormState({
              newUserEmail: newValue,
            });
          } else if (newValue && newValue.inputValue) {
            // Create a new value from the user input
            setFormState({
              newUserEmail: newValue.inputValue,
            });
          } else {
            setFormState({ newUserEmail: newValue.username });
          }
        }}
        filterOptions={(options, params) => {
          const filtered = filter(options, params);

          // Suggest the creation of a new value
          if (params.inputValue !== '') {
            filtered.push({
              inputValue: params.inputValue,
              username: `Add "${params.inputValue}"`,
            });
          }

          return filtered;
        }}
        selectOnFocus
        clearOnBlur
        handleHomeEndKeys
        options={allUsers}
        getOptionLabel={(option) => {
          // Value selected with enter, right from the input
          if (typeof option === 'string') {
            return option;
          }
          // Add "xxx" option created dynamically
          if (option.inputValue) {
            return option.inputValue;
          }
          // Regular option
          return option.username;
        }}
        renderOption={(option) => option.username}
        style={{ width: 300, paddingBottom: 10 }}
        freeSolo
        renderInput={(params) => (
          // eslint-disable-next-line react/jsx-props-no-spreading
          <TextField {...params} label="Enter user email" />
        )}
      />
      <input type="checkbox" checked={formState.admin} onChange={toggleAdmin} />
      Group Admin
      &nbsp;&nbsp;
      <input type="submit" onClick={handleSubmit} value="Add user" />
    </div>
  );
};
NewGroupUserForm.propTypes = {
  group_id: PropTypes.number.isRequired
};

export default NewGroupUserForm;
