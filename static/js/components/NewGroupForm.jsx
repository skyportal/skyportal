import React, { useState } from 'react';
import { useDispatch } from 'react-redux';

import * as Action from '../ducks/groups';
import styles from './NewGroupForm.css';


const NewGroupForm = (props) => {
  const dispatch = useDispatch();
  const [formState, setState] = useState({
    name: "",
    groupAdmins: ""
  });

  const handleSubmit = (event) => {
    event.preventDefault();
    dispatch(Action.addNewGroup(formState));
    setState({
      name: "",
      groupAdmins: ""
    });
  };

  const handleChange = (event) => {
    const newState = {};
    newState[event.target.name] = event.target.value;
    setState({
      ...formState,
      ...newState
    });
  };

  return (
    <div className={styles.newGroupFormDiv}>
      <h3>
        Create New Group
      </h3>
      <form className={styles.newGroupForm} onSubmit={handleSubmit}>
        <table>
          <tbody>
            <tr>
              <td>
                <label>
                  Group Name:
                  {' '}
                </label>
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
                <label>
                  Group Admins (comma-separated email addresses):
                  {' '}
                </label>
              </td>
              <td>
                <input
                  type="text"
                  name="groupAdmins"
                  value={formState.groupAdmins}
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
    </div>
  );
};

export default NewGroupForm;
