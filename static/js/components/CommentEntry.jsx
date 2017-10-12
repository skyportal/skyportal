import React from 'react';
import PropTypes from 'prop-types';

import styles from './CommentEntry.css';


class CommentEntry extends React.Component {
  constructor(props) {
    super(props);

    this.state = { value: '' };
    this._handleSubmit = this._handleSubmit.bind(this);
    this._handleChange = this._handleChange.bind(this);
  }

  _handleSubmit(event) {
    const { addComment } = this.props;

    event.preventDefault();
    addComment(this.state.value);
    this.setState({ value: "" });
  }

  _handleChange(event) {
    this.setState({ value: event.target.value });
  }

  render() {
    return (
      <form className={styles.commentEntry} onSubmit={this._handleSubmit}>
        <label>
          <input
            type="text"
            name="comment"
            value={this.state.value}
            onChange={this._handleChange}
          />
        </label>
        <input type="submit" value="↵" />
      </form>
    );
  }
}

CommentEntry.propTypes = {
  addComment: PropTypes.func.isRequired
};

export default CommentEntry;
