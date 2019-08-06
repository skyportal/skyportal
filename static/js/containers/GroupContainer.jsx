import React from 'react';
import PropTypes from 'prop-types';
import { connect } from 'react-redux';

import * as Action from '../actions';
import * as fetchGroupActions from '../ducks/fetchGroup';
import Group from '../components/Group';

class GroupContainer extends React.Component {
  componentDidMount() {
    const { id } = this.props.route;
    this.props.fetchGroup(id);
  }

  render() {
    return (
      <Group
        name={this.props.name}
        id={this.props.id}
        users={this.props.users}
        group_users={this.props.group_users}
        currentUser={this.props.currentUser}
        deleteGroupUser={this.props.deleteGroupUser}
      />
    );
  }
}

GroupContainer.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string
  }).isRequired,
  name: PropTypes.string.isRequired,
  id: PropTypes.number.isRequired,
  users: PropTypes.arrayOf(PropTypes.object).isRequired,
  group_users: PropTypes.arrayOf(PropTypes.object).isRequired,
  currentUser: PropTypes.object.isRequired,
  fetchGroup: PropTypes.func.isRequired,
  deleteGroupUser: PropTypes.func.isRequired
};

const mapStateToProps = (state, ownProps) => (
  {
    ...state.group,
    currentUser: state.profile
  }
);

const mapDispatchToProps = (dispatch, ownProps) => (
  {
    deleteGroupUser: (username, group_id) => dispatch(
      Action.deleteGroupUser({ username, group_id })
    ),
    fetchGroup: id => dispatch(
      fetchGroupActions.fetchGroup(id)
    )
  }
);

export default connect(mapStateToProps, mapDispatchToProps)(GroupContainer);
