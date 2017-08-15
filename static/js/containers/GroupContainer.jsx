import React from 'react';
import { connect } from 'react-redux';

import * as Action from '../actions';
import Group from '../components/Group';

class GroupContainer extends React.Component {
  componentDidMount() {
    let id = this.props.route.id;
    this.props.dispatch(Action.fetchGroup(id));
  }

  render = () => {
    return (
      <Group name={this.props.name} id={this.props.id} users={this.props.users}/>
    );
  };
}

const mapStateToProps = (state, ownProps) => {
  return state.group;
};

export default connect(mapStateToProps)(GroupContainer);
