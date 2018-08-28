import React from 'react';
import PropTypes from 'prop-types';

import styles from './NewGroupForm.css';


class NewGroupForm extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      groupName: "",
      groupAdmins: ""
    };
    this.handleSubmit = this.handleSubmit.bind(this);
    this.handleChange = this.handleChange.bind(this);
  }

  handleSubmit(event) {
    event.preventDefault();
    this.props.addNewGroup(this.state);
    this.setState({
      groupName: "",
      groupAdmins: ""
    });
  }

  handleChange(event) {
    const newState = {};
    newState[event.target.name] = event.target.value;
    this.setState(newState);
  }

  render() {
    return (
      <div className={styles.newGroupFormDiv}>
        <h3>
Create New Group
        </h3>
        <form className={styles.newGroupForm} onSubmit={this.handleSubmit}>
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
                    name="groupName"
                    value={this.state.groupName}
                    onChange={this.handleChange}
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
                    value={this.state.groupAdmins}
                    onChange={this.handleChange}
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
  }
}
NewGroupForm.propTypes = {
  addNewGroup: PropTypes.func.isRequired
};

export default NewGroupForm;
