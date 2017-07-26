import React from 'react';
import { connect } from 'react-redux';

import * as Action from '../actions';
import CommentList from '../components/CommentList';

class CommentListContainer extends React.Component {
  componentDidMount() {
    this.props.dispatch(Action.fetchComments(this.props.source));
  }

  render = () => {
    return <CommentList comments={this.props.comments}
                        source={this.props.source}/>;
  };
}

const mapStateToProps = (state, ownProps) => (
  {
    comments: state.comments[ownProps.source] || []
  }
);

export default connect(mapStateToProps)(CommentListContainer);
