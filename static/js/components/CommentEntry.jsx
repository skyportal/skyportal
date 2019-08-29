import React from 'react';
import PropTypes from 'prop-types';

import styles from './CommentEntry.css';


class CommentEntry extends React.Component {
  constructor(props) {
    super(props);

    this.state = {
      text: '',
      attachment: ''
    };
    this._handleSubmit = this._handleSubmit.bind(this);
    this._handleChange = this._handleChange.bind(this);
  }

  _handleSubmit(event) {
    const { addComment } = this.props;

    event.preventDefault();
    addComment(this.state);
    this.fileInput.value = "";
    this.setState({
      text: "",
      attachment: ""
    });
  }

  _handleChange(event) {
    if (event.target.files) {
      this.setState({ attachment: event.target.files[0] });
    } else {
      this.setState({ text: event.target.value });
    }
  }

  render() {
    return (
      <form className={styles.commentEntry} onSubmit={this._handleSubmit}>
        <div>
          <input
            type="text"
            name="comment"
            value={this.state.text}
            onChange={this._handleChange}
          />
        </div>
        <div>
          <label>
            Attachment &nbsp;
            <input
              ref={(el) => { this.fileInput = el; }}
              type="file"
              onChange={this._handleChange}
            />
          </label>
        </div>
        <input type="submit" value="↵" />
      </form>
    );
  }
}

CommentEntry.propTypes = {
  addComment: PropTypes.func.isRequired
};

export default CommentEntry;
