import React from 'react';
import PropTypes from 'prop-types';
import { connect } from 'react-redux';

import * as Action from '../actions';
import Group from '../components/Group';

class GroupContainer extends React.Component {
  componentDidMount() {
    const { id } = this.props.route;
    this.props.dispatch(Action.fetchGroup(id));
  }

  render() {
    return <Group
             name={this.props.name}
             id={this.props.id}
             users={this.props.users}
             currentUser={this.props.currentUser}
    />;
  }
}

GroupContainer.propTypes = {
  dispatch: PropTypes.func.isRequired,
  route: PropTypes.shape({
    id: PropTypes.string
  }).isRequired,
  name: PropTypes.string.isRequired,
  id: PropTypes.number.isRequired,
  users: PropTypes.arrayOf(PropTypes.object).isRequired
};

const mapStateToProps = (state, ownProps) => (
  {
    ...state.group,
    currentUser: state.profile
  }
);

export default connect(mapStateToProps)(GroupContainer);
