import React from 'react';
import PropTypes from 'prop-types';


class NewGroupUserForm extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      newUserEmail: "",
      admin: false
    };

    this.handleChange = this.handleChange.bind(this);
    this.handleSubmit = this.handleSubmit.bind(this);
    this.toggleAdmin = this.toggleAdmin.bind(this);
  }

  handleChange(event) {
    this.setState({ newUserEmail: event.target.value });
  }

  handleSubmit(event) {
    event.preventDefault();
    this.props.addGroupUser(this.state.newUserEmail, this.state.admin);
    this.setState({ newUserEmail: "" });
  }

  toggleAdmin(event) {
    this.setState({ admin: event.target.checked });
  }

  render() {
    return (
      <div>
        <input
          type="text"
          id="newUserEmail"
          value={this.state.newUserEmail}
          onChange={this.handleChange}
        />
        &nbsp;
        <input type="checkbox" onChange={this.toggleAdmin} />
Group Admin
        &nbsp;&nbsp;
        <input type="submit" onClick={this.handleSubmit} value="Add user" />
      </div>
    );
  }
}

NewGroupUserForm.propTypes = {
  addGroupUser: PropTypes.func.isRequired
};

export default NewGroupUserForm;
