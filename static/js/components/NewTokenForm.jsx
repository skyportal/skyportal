import React from 'react';
import PropTypes from 'prop-types';


class CreateTokenForm extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      group_id: "",
      description: ""
    };

    this.handleSubmit = this.handleSubmit.bind(this);
    this.handleChange = this.handleChange.bind(this);
  }

  handleSubmit(event) {
    event.preventDefault();
    this.props.createToken(this.state);
    const acls_state  = {};
    Object.keys(this.state).forEach(k => {
      if (k.startsWith('acls_')) {
        acls_state[k] = false;
      }
    });
    this.setState({
      group_id: "",
      description: "",
      ...acls_state
    });
  }

  handleChange(event) {
    const newState = {};
    newState[event.target.name] = event.target.type === 'checkbox' ?
                                  event.target.checked : event.target.value;
    this.setState(newState);
  }

  render() {
    if(!this.props.profile) {
      return <div></div>;
    }
    return (
      <div>
        <h3>Generate New Token for Command-Line Authentication</h3>
        <form onSubmit={this.handleSubmit}>
          <table>
            <tbody>
              <tr>
                <td>Select Token ACLs:</td>
                <td>
                  {this.props.profile.acls.map(acl =>
                    <label>
                      <input
                        type="checkbox"
                        name={`acls_${acl}`}
                        checked={this.state[`acls_${acl}`]}
                        onChange={this.handleChange}
                      />
                      {acl}
                    </label>
                  )}
                </td>
              </tr>
              <tr>
                <td>Select Token Group:</td>
                <td>
                  <select
                    name="group_id"
                    value={this.state.group_id}
                    onChange={this.handleChange}
                  >
                    <option value=""></option>
                    {this.props.groups.map(group =>
                      <option value={group.id}>{group.name}</option>
                    )}
                  </select>
                </td>
              </tr>
              <tr>
                <td>
                  <label>Token description: </label>
                </td>
                <td>
                  <input
                    type="text"
                    name="description"
                    value={this.state.description}
                    onChange={this.handleChange}
                  />
                </td>
              </tr>
              <tr>
                <td>
                  <input
                    type="submit"
                    value="Generate Token"
                    onClick={this.handleSubmit}
                  />
                </td>
              </tr>
            </tbody>
          </table>
        </form>
      </div>
    );
  }
}
CreateTokenForm.propTypes = {
  profile: PropTypes.object,
  groups: PropTypes.array
};

export default CreateTokenForm;
