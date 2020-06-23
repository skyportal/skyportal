import React, { useState } from "react";
import PropTypes from "prop-types";

import styles from "./CommentEntry.css";

const CommentEntry = ({ addComment }) => {
  const [state, setState] = useState({ text: "", attachment: "" });

  const handleSubmit = (event) => {
    event.preventDefault();
    addComment(state);
    this.fileInput.value = "";
    setState({
      text: "",
      attachment: ""
    });
  };

  const handleChange = (event) => {
    if (event.target.files) {
      setState({ ...state, attachment: event.target.files[0] });
    } else {
      setState({ ...state, text: event.target.value });
    }
  };

  return (
    <form className={styles.commentEntry} onSubmit={handleSubmit}>
      <div>
        <input
          type="text"
          name="comment"
          value={state.text}
          onChange={handleChange}
        />
      </div>
      <div>
        <label>
          Attachment &nbsp;
          <input
            ref={(el) => { this.fileInput = el; }}
            type="file"
            onChange={handleChange}
          />
        </label>
      </div>
      <input type="submit" value="↵" />
    </form>
  );
};

CommentEntry.propTypes = {
  addComment: PropTypes.func.isRequired
};

export default CommentEntry;
