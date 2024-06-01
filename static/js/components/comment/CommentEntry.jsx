import React, { useEffect, useMemo, useRef, useState } from "react";
import PropTypes from "prop-types";
import { useSelector } from "react-redux";
import { Controller, useForm } from "react-hook-form";
import Checkbox from "@mui/material/Checkbox";
import TextField from "@mui/material/TextField";
import makeStyles from "@mui/styles/makeStyles";
import FormControlLabel from "@mui/material/FormControlLabel";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";
import Button from "../Button";

import FormValidationError from "../FormValidationError";
import UsernameTrie from "../../usernameTrie";
import InstrumentTrie from "../../instrumentTrie";

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

const CommentEntry = ({
  addComment,
  editComment,
  commentText,
  attachmentName,
  closeDialog,
}) => {
  const styles = useStyles();
  const users = useSelector((state) => state.users);
  const { userAccessible: groups } = useSelector((state) => state.groups);
  const { instrumentList } = useSelector((state) => state.instruments);
  const [textValue, setTextValue] = useState("");
  const [textInputCursorIndex, setTextInputCursorIndex] = useState(0);
  const [autosuggestVisible, setAutosuggestVisible] = useState(false);
  const [textRequired, setTextRequired] = useState(false);
  const [usernamePrefixMatches, setUsernamePrefixMatches] = useState({});
  const [instrumentPrefixMatches, setInstrumentPrefixMatches] = useState({});
  const textAreaRef = useRef(null);
  const autoSuggestRootItem = useRef(null);

  const usernameTrie = useMemo(() => {
    const trie = UsernameTrie();
    (users?.users || []).forEach((user) => {
      if (!user.username) {
        return;
      }
      if (user.is_bot) {
        return;
      }
      trie.insertUser({
        username: user.username,
        firstName: user.first_name || "",
        lastName: user.last_name || "",
      });
    });
    return trie;
  }, [users]);

  const instrumentTrie = useMemo(() => {
    const trie = InstrumentTrie();
    instrumentList.forEach((instrument) => {
      trie.insertInstrument({
        instrument: instrument.name,
        telescope: instrument.telescope.nickname,
      });
    });
    return trie;
  }, [instrumentList]);

  const {
    handleSubmit,
    reset,
    register,
    getValues,
    setValue,
    control,

    formState: { errors },
  } = useForm();

  // The file input needs to be registered here, not in the input tag below
  useEffect(() => {
    register("name", { name: "attachment" });
  }, [register]);

  useEffect(() => {
    if (addComment) {
      setTextRequired(true);
    } else if (editComment) {
      setTextRequired(false);
      if (commentText) {
        setTextValue(commentText);
      }
    }
  }, [addComment, editComment, commentText]);

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
    if (addComment) {
      addComment(data);
    } else if (editComment) {
      editComment(data);
    }
    reset();
    setGroupSelectVisible(false);
    setTextValue("");
    setAutosuggestVisible(false);
    setUsernamePrefixMatches({});
    if (closeDialog) {
      closeDialog();
    }
  };

  const handleTextInputChange = (event) => {
    const text = event.target.value;
    const cursorIdx = event.target.selectionStart;
    const currentWord = text.slice(0, cursorIdx).split(" ").pop();
    if (currentWord.startsWith("@")) {
      const matches = usernameTrie.findAllStartingWith(
        currentWord.slice(1),
        10,
      );
      setUsernamePrefixMatches(matches);
      if (Object.keys(matches).length > 0) {
        setTextInputCursorIndex(cursorIdx);
        setAutosuggestVisible(true);
      }
    } else if (currentWord.startsWith("#")) {
      const matches = instrumentTrie.findAllStartingWith(
        currentWord.slice(1),
        10,
      );
      setInstrumentPrefixMatches(matches);
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
    const formState = getValues();
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
      textInputCursorIndex - currentWord.length,
    )}@${username} ${textValue.slice(textInputCursorIndex)}`;

    setTextValue(newTextValue);
    setValue("text", newTextValue);
    setAutosuggestVisible(false);
    setUsernamePrefixMatches({});
    textAreaRef.current.focus();
  };

  const handleClickSuggestedInstrument = (instrument) => {
    const currentWord = textValue
      .slice(0, textInputCursorIndex)
      .trim()
      .split(" ")
      .pop();

    const newTextValue = `${textValue.slice(
      0,
      textInputCursorIndex - currentWord.length,
    )}#${instrument} ${textValue.slice(textInputCursorIndex)}`;

    setTextValue(newTextValue);
    setValue("text", newTextValue);
    setAutosuggestVisible(false);
    setInstrumentPrefixMatches({});
    textAreaRef.current.focus();
  };

  return (
    <form className={styles.commentEntry} onSubmit={handleSubmit(onSubmit)}>
      {addComment ? <Typography variant="h6">Add comment</Typography> : <></>}
      {editComment ? <Typography variant="h6">Edit comment</Typography> : <></>}
      <div className={styles.inputDiv}>
        <Controller
          render={() => (
            <div>
              <div>
                {addComment ? (
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
                ) : (
                  <></>
                )}
              </div>
              <div>
                {editComment ? (
                  <TextField
                    id="root_comment"
                    value={textValue}
                    onChange={(event) => {
                      handleTextInputChange(event);
                    }}
                    label="Comment text"
                    name="text"
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
                ) : (
                  <></>
                )}
              </div>
            </div>
          )}
          name="text"
          control={control}
          rules={{ required: textRequired }}
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
          ),
        )}
      </div>
      <div
        style={{
          paddingLeft: "2rem",
          overflowY: "scroll",
          maxHeight: "10rem",
          display: autosuggestVisible ? "block" : "none",
        }}
      >
        {Object.entries(instrumentPrefixMatches).map(
          ([instrument, { telescope }], ix) => (
            <li key={instrument}>
              <Button
                onClick={() => handleClickSuggestedInstrument(instrument)}
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
                {`${instrument} / ${telescope}`.trim()}
              </Button>
            </li>
          ),
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
        {editComment && attachmentName && !getValues()?.attachment && (
          // show a msg that says that the comment being edited has an attachment already
          // and that it will be replaced if a new attachment is uploaded
          // should me in parenthesis and italic, and the attachment name should be bold
          <Typography variant="caption" style={{ fontStyle: "italic" }}>
            (Current attachment: <strong>{attachmentName}</strong>, will be
            replaced if a new attachment is uploaded)
          </Typography>
        )}
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
                  render={({ field: { onChange, value } }) => (
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
        <Button primary type="submitComment" name="submitCommentButton">
          {addComment ? <>Add Comment</> : ""}
          {editComment ? <>Edit Comment</> : ""}
        </Button>
      </div>
    </form>
  );
};

CommentEntry.propTypes = {
  addComment: PropTypes.func,
  editComment: PropTypes.func,
  commentText: PropTypes.string,
  attachmentName: PropTypes.string,
  closeDialog: PropTypes.func,
};

CommentEntry.defaultProps = {
  addComment: null,
  editComment: null,
  commentText: "",
  attachmentName: "",
  closeDialog: null,
};

export default CommentEntry;
