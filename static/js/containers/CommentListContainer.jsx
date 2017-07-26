import React from 'react';
import { connect } from 'react-redux';

import * as Action from '../actions';
import CommentList from '../components/CommentList';


class CommentListContainer extends React.Component {
  componentDidMount() {
    this.props.fetchComments();
  }

  render = () => {
    return (
      <CommentList comments={this.props.comments}
                   source={this.props.source}
                   addComment={this.props.addComment}/>
    );
  };
}

const mapStateToProps = (state, ownProps) => (
  {
    comments: state.comments[ownProps.source] || []
  }
);

const mapDispatchToProps = (dispatch, ownProps) => (
  {
    fetchComments: () => dispatch(Action.fetchComments(ownProps.source)),
    addComment: ({text}) => dispatch(Action.addComment(ownProps.source, text))
  }
);

export default connect(mapStateToProps, mapDispatchToProps)(CommentListContainer);
