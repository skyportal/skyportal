import React from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom';

import NewGroupUserForm from '../containers/NewGroupUserForm';
import styles from "./Group.css";


class Group extends React.Component {
  constructor(props) {
    super(props);
    this.handleDeleteGroupUser = this.handleDeleteGroupUser.bind(this);
  }
  handleDeleteGroupUser(username, group_id) {
    this.props.deleteGroupUser(username, group_id);
  }
  render() {
    if (this.props.id === undefined) {
      return <div>Group not found</div>;
    } else {
      return (
        <div className={styles.group}>
          { /* <div className={styles.name}>{id}</div> */ }
          <b>Group Name: </b>{this.props.name}
          <ul>
            {
              this.props.users.map((user, idx) => (
                <li key={user.id}>
                  <Link to={`/users/${user.id}`}>{user.username}</Link>&nbsp;&nbsp;
                  {
                    this.props.group_users.filter(group_user =>
                      group_user.user_id == user.id)[0].admin &&
                      <div style={{ display: "inline-block" }}>
                        <span className={styles.badge}>Admin</span>&nbsp;&nbsp;
                      </div>
                  }
                  {
                    (this.props.currentUser.roles.includes('Super admin') ||
                     this.props.currentUser.roles.includes('Group admin')) &&
                      <input
                        type="submit"
                        onClick={() => this.props.deleteGroupUser(user.username,
                                                                  this.props.id)}
                        value="Remove from group"
                      />
                  }
                </li>
              ))
            }
          </ul>
          {
            (this.props.currentUser.roles.includes('Super admin') ||
             this.props.currentUser.roles.includes('Group admin')) &&
             <NewGroupUserForm group_id={this.props.id} />
          }
        </div>
      );
    }
  }
}

Group.propTypes = {
  name: PropTypes.string.isRequired,
  id: PropTypes.number.isRequired,
  users: PropTypes.arrayOf(PropTypes.object).isRequired,
  group_users: PropTypes.arrayOf(PropTypes.object).isRequired,
  currentUser: PropTypes.object.isRequired,
  deleteGroupUser: PropTypes.func.isRequired
};


export default Group;
