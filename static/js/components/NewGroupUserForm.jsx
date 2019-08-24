import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { useDispatch } from 'react-redux';

import * as Action from '../ducks/groups';

const NewGroupUserForm = ({ group_id }) => {
  const dispatch = useDispatch();
  const [formState, setState] = useState({
    newUserEmail: "",
    admin: false
  });

  const handleChange = (event) => {
    setState({
      ...formState,
      newUserEmail: event.target.value
    });
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    dispatch(Action.addGroupUser({
      username: formState.newUserEmail,
      admin: formState.admin,
      group_id
    }));
    setState({
      newUserEmail: "",
      admin: false
    });
  };

  const toggleAdmin = (event) => {
    setState({
      ...formState,
      admin: event.target.checked
    });
  };

  return (
    <div>
      <input
        type="text"
        id="newUserEmail"
        value={formState.newUserEmail}
        onChange={handleChange}
      />
      &nbsp;
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
