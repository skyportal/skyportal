import React, { useEffect, useState, useMemo, useRef } from "react";
import PropTypes from "prop-types";
import { useSelector } from "react-redux";
import { useForm, Controller } from "react-hook-form";
import Checkbox from "@material-ui/core/Checkbox";
import TextField from "@material-ui/core/TextField";
import { makeStyles } from "@material-ui/core/styles";
import FormControlLabel from "@material-ui/core/FormControlLabel";
import Typography from "@material-ui/core/Typography";
import Button from "@material-ui/core/Button";
import Box from "@material-ui/core/Box";

import FormValidationError from "./FormValidationError";
import UsernameTrie from "../usernameTrie";

const useStyles = makeStyles(() => ({
  commentEntry: {
    position: "relative",
  },
  inputDiv: {
    padding: "0.3rem",
    position: "relative",
  },
  customizeGroupsContainer: {
    flexWrap: "wrap",
    width: "25rem",
  },
}));

const CommentEntry = ({ addComment }) => {
  const styles = useStyles();
  const { userAccessible: groups } = useSelector((state) => state.groups);
  const [textValue, setTextValue] = useState("");
  const [textInputCursorIndex, setTextInputCursorIndex] = useState(0);
  const [autosuggestVisible, setAutosuggestVisible] = useState(false);
  const [usernamePrefixMatches, setUsernamePrefixMatches] = useState({});
  const textAreaRef = useRef(null);
  const autoSuggestRootItem = useRef(null);
  const { users } = useSelector((state) => state.users);

  const usernameTrie = useMemo(() => {
    const trie = UsernameTrie();
    users.forEach((user) => {
      trie.insertUser({
        username: user.username,
        firstName: user.first_name || "",
        lastName: user.last_name || "",
      });
    });
    return trie;
  }, [users]);

  const {
    handleSubmit,
    reset,
    register,
    getValues,
    setValue,
    control,
    errors,
  } = useForm();

  // The file input needs to be registered here, not in the input tag below
  useEffect(() => {
    register({ name: "attachment" });
  }, [register]);

  useEffect(() => {
    reset({
      group_ids: Array(groups.length).fill(true),
    });
  }, [reset, groups]);

  const [groupSelectVisible, setGroupSelectVisible] = useState(false);
  const toggleGroupSelectVisible = () => {
    setGroupSelectVisible(!groupSelectVisible);
  };

  const onSubmit = (data) => {
    const groupIDs = groups?.map((g) => g.id);
    const selectedGroupIDs = groupIDs?.filter((ID, idx) => data.group_ids[idx]);
    data.group_ids = selectedGroupIDs;
    addComment(data);
    reset();
    setGroupSelectVisible(false);
    setTextValue("");
    setAutosuggestVisible(false);
    setUsernamePrefixMatches({});
  };

  const handleTextInputChange = (event) => {
    const text = event.target.value;
    const cursorIdx = event.target.selectionStart;
    const currentWord = text.slice(0, cursorIdx).split(" ").pop();
    if (currentWord.startsWith("@")) {
      const matches = usernameTrie.findAllStartingWith(
        currentWord.slice(1),
        10
      );
      setUsernamePrefixMatches(matches);
      if (Object.keys(matches).length > 0) {
        setTextInputCursorIndex(cursorIdx);
        setAutosuggestVisible(true);
      }
    } else {
      setAutosuggestVisible(false);
    }
    setTextValue(text);
    // RHF-specific state
    setValue("text", text);
  };

  const handleFileInputChange = (event) => {
    const file = event.target.files[0];
    setValue("attachment", file);
  };

  const validateGroups = () => {
    const formState = getValues({ nest: true });
    return formState.group_ids?.filter((value) => Boolean(value)).length >= 1;
  };

  const handleClickSuggestedUsername = (username) => {
    const currentWord = textValue
      .slice(0, textInputCursorIndex)
      .trim()
      .split(" ")
      .pop();

    const newTextValue = `${textValue.slice(
      0,
      textInputCursorIndex - currentWord.length
    )}@${username} ${textValue.slice(textInputCursorIndex)}`;

    setTextValue(newTextValue);
    setValue("text", newTextValue);
    setAutosuggestVisible(false);
    setUsernamePrefixMatches({});
    textAreaRef.current.focus();
  };

  return (
    <form className={styles.commentEntry} onSubmit={handleSubmit(onSubmit)}>
      <Typography variant="h6">Add comment</Typography>
      <div className={styles.inputDiv}>
        <Controller
          render={() => (
            <TextField
              id="root_comment"
              value={textValue}
              onChange={(event) => {
                handleTextInputChange(event);
              }}
              label="Comment text"
              name="text"
              error={!!errors.text}
              helperText={errors.text ? "Required" : ""}
              fullWidth
              multiline
              inputRef={textAreaRef}
              onKeyDown={(event) => {
                // On down arrow, move focus to autocomplete
                if (event.key === "ArrowDown" && autosuggestVisible) {
                  autoSuggestRootItem.current.focus();
                  // Do not scroll the list
                  event.preventDefault();
                }
              }}
            />
          )}
          name="text"
          control={control}
          rules={{ required: true }}
          defaultValue=""
        />
      </div>
      <div
        style={{
          paddingLeft: "2rem",
          overflowY: "scroll",
          maxHeight: "10rem",
          display: autosuggestVisible ? "block" : "none",
        }}
      >
        {Object.entries(usernamePrefixMatches).map(
          ([username, { firstName, lastName }], ix) => (
            <li key={username}>
              <Button
                onClick={() => handleClickSuggestedUsername(username)}
                style={{ textTransform: "none" }}
                ref={ix === 0 ? autoSuggestRootItem : null}
                onKeyDown={(event) => {
                  // On down arrow, move to next sibling
                  if (event.key === "ArrowDown") {
                    // Focus on next item in list
                    // -> parent (li) -> sibling (li) -> firstChild (button)
                    event.target.parentNode.nextSibling?.firstChild.focus();
                    // Do not scroll the list
                    event.preventDefault();
                  }
                  // Up arrow
                  if (event.key === "ArrowUp") {
                    // Focus on previous item in list
                    // -> parent (li) -> sibling (li) -> firstChild (button)
                    event.target.parentNode.previousSibling?.firstChild.focus();
                    event.preventDefault();
                  }
                }}
              >
                {`${username} ${firstName || ""} ${lastName || ""}`.trim()}
              </Button>
            </li>
          )
        )}
      </div>
      <div className={styles.inputDiv}>
        <label>
          Attachment &nbsp;
          <input
            type="file"
            name="attachment"
            onChange={handleFileInputChange}
          />
        </label>
      </div>
      <div className={styles.inputDiv}>
        {errors.group_ids && (
          <FormValidationError message="Select at least one group." />
        )}
        <Button
          onClick={toggleGroupSelectVisible}
          size="small"
          style={{ textTransform: "none" }}
        >
          Customize Group Access
        </Button>
        <Box
          component="div"
          display={groupSelectVisible ? "flex" : "none"}
          className={styles.customizeGroupsContainer}
        >
          {groups?.map((userGroup, idx) => (
            <FormControlLabel
              key={userGroup.id}
              control={
                <Controller
                  render={({ onChange, value }) => (
                    <Checkbox
                      onChange={(event) => onChange(event.target.checked)}
                      checked={value}
                      data-testid={`commentGroupCheckBox${userGroup.id}`}
                    />
                  )}
                  name={`group_ids[${idx}]`}
                  defaultValue
                  control={control}
                  rules={{ validate: validateGroups }}
                />
              }
              label={userGroup.name}
            />
          ))}
        </Box>
      </div>
      <div className={styles.inputDiv}>
        <Button
          variant="contained"
          color="primary"
          type="submitComment"
          name="submitCommentButton"
        >
          Add Comment
        </Button>
      </div>
    </form>
  );
};

CommentEntry.propTypes = {
  addComment: PropTypes.func.isRequired,
};

export default CommentEntry;
