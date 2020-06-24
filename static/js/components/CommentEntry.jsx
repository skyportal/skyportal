import React, { useEffect } from "react";
import PropTypes from "prop-types";
import { useForm } from "react-hook-form";

import styles from "./CommentEntry.css";

const CommentEntry = ({ addComment }) => {
  const { handleSubmit, reset, register, getValues, setValue } = useForm({
    text: "",
    attachment: ""
  });

  // The file input needs to be registered here, not in the input tag below
  useEffect(() => {
    register({ name: "attachment" });
  }, [register]);

  const onSubmit = () => {
    addComment(getValues());
    reset({
      text: "",
      attachment: ""
    });
  };

  const handleFileInputChange = (event) => {
    const file = event.target.files[0];
    setValue("attachment", file);
  };

  return (
    <form className={styles.commentEntry} onSubmit={handleSubmit(onSubmit)}>
      <div>
        <input
          type="text"
          name="text"
          ref={register}
        />
      </div>
      <div>
        <label>
          Attachment &nbsp;
          <input
            type="file"
            name="attachment"
            onChange={handleFileInputChange}
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
