import React from 'react';
import PropTypes from 'prop-types';

import * as Actions from '../actions';


class NewGroupUserForm extends React.Component {
  constructor(props) {
    super(props);
    this.state = { newUserEmail: "" };

    this.handleChange = this.handleChange.bind(this);
    this.handleSubmit = this.handleSubmit.bind(this);
  }
  handleChange(event) {
    this.setState({ newUserEmail: event.target.value });
  }
  handleSubmit(event) {
    event.preventDefault();
    this.props.addGroupUser(this.state.newUserEmail);
    this.setState({ newUserEmail: "" });
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
        <input type="submit" onClick={this.handleSubmit} value="Add user" />
      </div>
    );
  }
}


export default NewGroupUserForm;
