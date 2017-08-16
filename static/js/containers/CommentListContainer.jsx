import React from 'react';
import { connect } from 'react-redux';

import * as Action from '../actions';
import CommentList from '../components/CommentList';


class CommentListContainer extends React.Component {
  render = () => {
    return (
      <CommentList comments={this.props.source.comments}
                   source_id={this.props.source.id}
                   addComment={this.props.addComment}/>
    );
  };
}

const mapStateToProps = (state, ownProps) => (
  {
    source: state.source
  }
);

const mapDispatchToProps = (dispatch, ownProps) => (
  {
    addComment: (text) => dispatch(
      Action.addComment({source_id: ownProps.source, text})
    )
  }
);

export default connect(mapStateToProps, mapDispatchToProps)(CommentListContainer);
