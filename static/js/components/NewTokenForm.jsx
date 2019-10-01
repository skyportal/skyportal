import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { useDispatch } from 'react-redux';

import * as Action from '../ducks/profile';


const CreateTokenForm = ({ profile, groups }) => {
  const dispatch = useDispatch();
  const [formState, setFormState] = useState({
    group_id: "",
    name: ""
  });
  const handleSubmit = (event) => {
    event.preventDefault();
    dispatch(Action.createToken(formState));
    const acls_state = {};
    Object.keys(formState).forEach((k) => {
      if (k.startsWith('acls_')) {
        acls_state[k] = false;
      }
    });
    setFormState({
      group_id: "",
      name: "",
      ...acls_state
    });
  };

  const handleChange = (event) => {
    const newState = {};
    newState[event.target.name] = event.target.type === 'checkbox' ?
      event.target.checked : event.target.value;
    setFormState({
      ...formState,
      ...newState
    });
  };

  if (!profile) {
    return <div />;
  }
  return (
    <div>
      <h3>
Generate New Token for Command-Line Authentication
      </h3>
      <form onSubmit={handleSubmit}>
        <table>
          <tbody>
            <tr>
              <td>
Select Token ACLs:
              </td>
              <td>
                {profile.acls.map((acl) => (
                  <label key={acl}>
                    <input
                      key={acl}
                      type="checkbox"
                      name={`acls_${acl}`}
                      checked={formState[`acls_${acl}`]}
                      onChange={handleChange}
                    />
                    {acl}
                  </label>
                ))}
              </td>
            </tr>
            <tr>
              <td>
                Select Token Group:
              </td>
              <td>
                <select
                  name="group_id"
                  value={formState.group_id}
                  onChange={handleChange}
                >
                  <option value="" />
                  {groups.map((group) => (
                    <option value={group.id} key={group.id}>
                      {group.name}
                    </option>
                  ))}
                </select>
              </td>
            </tr>
            <tr>
              <td>
                <label>
                  Token name:&nbsp;&nbsp;
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
                <input
                  type="submit"
                  value="Generate Token"
                  onClick={handleSubmit}
                />
              </td>
            </tr>
          </tbody>
        </table>
      </form>
    </div>
  );
};
CreateTokenForm.propTypes = {
  profile: PropTypes.object.isRequired,
  groups: PropTypes.array.isRequired
};

export default CreateTokenForm;
