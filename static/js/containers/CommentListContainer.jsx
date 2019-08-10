import React from 'react';
import PropTypes from 'prop-types';
import { connect } from 'react-redux';

import * as Action from '../actions';
import CommentList from '../components/CommentList';


const CommentListContainer = ({ source, addComment, userProfile, deleteComment }) => (
  <CommentList
    comments={source.comments}
    source_id={source.id}
    addComment={addComment}
    userProfile={userProfile}
    deleteComment={deleteComment}
  />
);

CommentListContainer.propTypes = {
  source: PropTypes.shape({
    comments: PropTypes.arrayOf(PropTypes.object),
    id: PropTypes.string
  }).isRequired,
  addComment: PropTypes.func.isRequired,
  userProfile: PropTypes.shape({
    roles: PropTypes.array,
    username: PropTypes.string
  }).isRequired,
  deleteComment: PropTypes.func.isRequired
};

const mapStateToProps = (state, ownProps) => (
  {
    source: state.source,
    userProfile: state.profile
  }
);

const mapDispatchToProps = (dispatch, ownProps) => (
  {
    addComment: formData => dispatch(
      Action.addComment({ source_id: ownProps.source, ...formData })
    ),
    deleteComment: comment_id => dispatch(
      Action.deleteComment(comment_id)
    )
  }
);

export default connect(mapStateToProps, mapDispatchToProps)(CommentListContainer);
