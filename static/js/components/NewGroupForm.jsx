import React, { useState } from 'react';
import { useDispatch } from 'react-redux';

import Box from '@material-ui/core/Box';

import * as Action from '../ducks/groups';
import styles from './NewGroupForm.css';


const NewGroupForm = () => {
  const dispatch = useDispatch();
  const [formState, setState] = useState({
    name: "",
    group_admins: []
  });

  const handleSubmit = (event) => {
    event.preventDefault();
    dispatch(Action.addNewGroup(formState));
    setState({
      name: "",
      group_admins: []
    });
  };

  const handleChange = (event) => {
    const newState = {};
    newState[event.target.name] = (event.target.name === "groupAdmins" ?
      event.target.value.split(",") : event.target.value);
    setState({
      ...formState,
      ...newState
    });
  };

  return (
    <Box p={1}>
      <h3>
        Create New Group
      </h3>
      <form className={styles.newGroupForm} onSubmit={handleSubmit}>
        <table>
          <tbody>
            <tr>
              <td>
                Group Name:&nbsp;&nbsp;
              </td>
              <td>
                <input
                  type="text"
                  name="name"
                  value={formState.name}
                  onChange={handleChange}
                />
              </td>
            </tr>
            <tr>
              <td>
                Group Admins (comma-separated email addresses):&nbsp;&nbsp;
              </td>
              <td>
                <input
                  type="text"
                  name="groupAdmins"
                  value={formState.group_admins}
                  onChange={handleChange}
                />
              </td>
            </tr>
            <tr>
              <td colSpan="2">
                <input type="submit" value="Create Group" />
              </td>
            </tr>
          </tbody>
        </table>
      </form>
    </Box>
  );
};

export default NewGroupForm;
