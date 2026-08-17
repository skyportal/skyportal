import { useEffect, useMemo, useRef, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import AttachFileIcon from "@mui/icons-material/AttachFile";
import GroupIcon from "@mui/icons-material/Group";
import SendIcon from "@mui/icons-material/Send";
import Checkbox from "@mui/material/Checkbox";
import IconButton from "@mui/material/IconButton";
import ListItemText from "@mui/material/ListItemText";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import { makeStyles } from "tss-react/mui";
import Typography from "@mui/material/Typography";

import { useGetGroupsQuery } from "../../ducks/groups";
import Button from "../Button";

import UsernameTrie from "../../usernameTrie";
import InstrumentTrie from "../../instrumentTrie";
import { useGetInstrumentsQuery } from "../../ducks/instruments";
import { useGetUsersQuery } from "../../ducks/users";

const useStyles = makeStyles()((theme) => ({
  commentEntry: {
    position: "relative",
  },
  composer: {
    display: "flex",
    alignItems: "flex-end",
    gap: "0.25rem",
    padding: theme.spacing(1, 1, 1.5),
  },
  suggestionsPopup: {
    position: "absolute",
    bottom: "100%",
    left: 0,
    right: 0,
    zIndex: 1,
    backgroundColor: theme.palette.background.paper,
    borderTop: `1px solid ${theme.palette.divider}`,
  },
  groupMenu: {
    maxHeight: "20rem",
    width: "18rem",
  },
  groupFilter: {
    position: "sticky",
    top: 0,
    zIndex: 1,
    padding: theme.spacing(0.5, 1, 1),
    backgroundColor: theme.palette.background.paper,
  },
  extras: {
    display: "flex",
    flexWrap: "wrap",
    alignItems: "center",
    padding: theme.spacing(0, 1),
  },
}));

interface CommentComposerProps {
  addComment?: ((...a: any[]) => void) | null;
  editComment?: ((...a: any[]) => void) | null;
  commentText?: string;
  attachmentName?: string;
  closeDialog?: (() => void) | null;
}

const CommentForm = ({
  addComment = null,
  editComment = null,
  commentText = "",
  attachmentName = "",
  closeDialog = null,
}: CommentComposerProps) => {
  const { classes: styles } = useStyles();
  const users = useGetUsersQuery().data ?? { users: [] };
  const { data: groupsData } = useGetGroupsQuery();
  const groups = useMemo(() => groupsData?.userAccessible ?? [], [groupsData]);
  const { data: instrumentList = [] } = useGetInstrumentsQuery();
  const [textValue, setTextValue] = useState("");
  const [fileName, setFileName] = useState("");
  const [groupAnchor, setGroupAnchor] = useState<HTMLElement | null>(null);
  const [groupFilter, setGroupFilter] = useState("");
  const [selectedGroups, setSelectedGroups] = useState<number[]>([]);
  const [textInputCursorIndex, setTextInputCursorIndex] = useState(0);
  const [autosuggestVisible, setAutosuggestVisible] = useState(false);
  const [textRequired, setTextRequired] = useState(false);
  const [usernamePrefixMatches, setUsernamePrefixMatches] = useState<
    Record<string, any>
  >({});
  const [instrumentPrefixMatches, setInstrumentPrefixMatches] = useState<
    Record<string, any>
  >({});
  const textAreaRef = useRef<any>(null);
  const autoSuggestRootItem = useRef<any>(null);

  const usernameTrie = useMemo(() => {
    const trie = UsernameTrie();
    ((users as any)?.users || []).forEach((user: any) => {
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
    instrumentList.forEach((instrument: any) => {
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
    setValue,
    control,

    formState: { errors },
  } = useForm();

  // The file input needs to be registered here, not in the input tag below
  useEffect(() => {
    register("name", { name: "attachment" } as any);
  }, [register]);

  const isAdd = Boolean(addComment);
  const isEdit = Boolean(editComment);

  useEffect(() => {
    if (isAdd) {
      setTextRequired(true);
    } else if (isEdit) {
      setTextRequired(false);
    }
  }, [isAdd, isEdit]);

  useEffect(() => {
    if (isEdit && commentText) {
      setTextValue(commentText);
    }
  }, [isEdit, commentText]);

  useEffect(() => {
    reset({
      group_ids: Array(groups.length).fill(false),
    });
  }, [reset, groups]);

  const toggleGroup = (idx: number) => {
    const selected = selectedGroups.includes(idx);
    setValue(`group_ids[${idx}]`, !selected);
    setSelectedGroups(
      selected
        ? selectedGroups.filter((i) => i !== idx)
        : [...selectedGroups, idx],
    );
  };

  const onSubmit = (data: any) => {
    const groupIDs = groups?.map((g) => g.id);
    const selectedGroupIDs = groupIDs?.filter(
      (_ID: any, idx: number) => data.group_ids[idx],
    );
    data.group_ids = selectedGroupIDs;
    if (addComment) {
      addComment(data);
    } else if (editComment) {
      editComment(data);
    }
    reset();
    setTextValue("");
    setFileName("");
    setSelectedGroups([]);
    setGroupFilter("");
    setAutosuggestVisible(false);
    setUsernamePrefixMatches({});
    if (closeDialog) {
      closeDialog();
    }
  };

  const handleTextInputChange = (event: any) => {
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

  const handleFileInputChange = (event: any) => {
    const file = event.target.files[0];
    setValue("attachment", file);
    setFileName(file?.name ?? "");
  };

  const handleComposerKeyDown = (event: any) => {
    if (event.key === "ArrowDown" && autosuggestVisible) {
      autoSuggestRootItem.current.focus();
      event.preventDefault();
    } else if (
      event.key === "Enter" &&
      !event.shiftKey &&
      !autosuggestVisible
    ) {
      event.preventDefault();
      handleSubmit(onSubmit)();
    }
  };

  const handleClickSuggestedUsername = (username: string) => {
    const currentWord = textValue
      .slice(0, textInputCursorIndex)
      .trim()
      .split(" ")
      .pop() as string;

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

  const handleClickSuggestedInstrument = (instrument: string) => {
    const currentWord = textValue
      .slice(0, textInputCursorIndex)
      .trim()
      .split(" ")
      .pop() as string;

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

  const suggestions = (
    <div
      className={addComment ? styles.suggestionsPopup : undefined}
      style={{ display: autosuggestVisible ? "block" : "none" }}
    >
      <div
        style={{ paddingLeft: "2rem", overflowY: "auto", maxHeight: "10rem" }}
      >
        {Object.entries(usernamePrefixMatches).map(
          ([username, { firstName, lastName }]: [string, any], ix) => (
            <li key={username}>
              <Button
                onClick={() => handleClickSuggestedUsername(username)}
                style={{ textTransform: "none" }}
                ref={ix === 0 ? autoSuggestRootItem : null}
                onKeyDown={(event: any) => {
                  if (event.key === "ArrowDown") {
                    event.target.parentNode.nextSibling?.firstChild.focus();
                    event.preventDefault();
                  }
                  if (event.key === "ArrowUp") {
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
        style={{ paddingLeft: "2rem", overflowY: "auto", maxHeight: "10rem" }}
      >
        {Object.entries(instrumentPrefixMatches).map(
          ([instrument, { telescope }]: [string, any], ix) => (
            <li key={instrument}>
              <Button
                onClick={() => handleClickSuggestedInstrument(instrument)}
                style={{ textTransform: "none" }}
                ref={ix === 0 ? autoSuggestRootItem : null}
                onKeyDown={(event: any) => {
                  if (event.key === "ArrowDown") {
                    event.target.parentNode.nextSibling?.firstChild.focus();
                    event.preventDefault();
                  }
                  if (event.key === "ArrowUp") {
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
    </div>
  );

  return (
    <form
      id={editComment ? "edit-comment-form" : undefined}
      className={styles.commentEntry}
      onSubmit={handleSubmit(onSubmit)}
      data-testid="comment-form"
    >
      {suggestions}
      {(fileName || attachmentName) && (
        <div className={styles.extras}>
          {fileName ? (
            <Typography variant="caption">{fileName}</Typography>
          ) : (
            attachmentName && (
              <Typography variant="caption" style={{ fontStyle: "italic" }}>
                (Current attachment: <strong>{attachmentName}</strong>, replaced
                if a new one is uploaded)
              </Typography>
            )
          )}
        </div>
      )}
      <div className={styles.composer}>
        <Controller
          render={() => (
            <TextField
              id="root_comment"
              value={textValue}
              onChange={handleTextInputChange}
              placeholder={editComment ? "Edit comment" : "Add a comment"}
              name="text"
              error={!!errors["text"]}
              size="small"
              fullWidth
              multiline
              maxRows={4}
              inputRef={textAreaRef}
              onKeyDown={handleComposerKeyDown}
            />
          )}
          name="text"
          control={control}
          rules={{ required: textRequired }}
        />
        <Tooltip title="Attachment">
          <IconButton component="label" size="small">
            <AttachFileIcon fontSize="small" />
            <input
              hidden
              type="file"
              name="attachment"
              onChange={handleFileInputChange}
            />
          </IconButton>
        </Tooltip>
        <Tooltip
          title={
            selectedGroups.length
              ? `Shared with ${selectedGroups.length} group(s)`
              : "Customize group access (public if not specified)"
          }
        >
          <IconButton
            size="small"
            color={selectedGroups.length ? "primary" : "default"}
            onClick={(event) => setGroupAnchor(event.currentTarget)}
            data-testid="customizeGroupsButton"
          >
            <GroupIcon fontSize="small" />
          </IconButton>
        </Tooltip>
        <Menu
          anchorEl={groupAnchor}
          open={Boolean(groupAnchor)}
          onClose={() => setGroupAnchor(null)}
          slotProps={{ paper: { className: styles.groupMenu } }}
        >
          <div className={styles.groupFilter}>
            <TextField
              autoFocus
              fullWidth
              size="small"
              placeholder="Filter groups"
              value={groupFilter}
              onChange={(event) => setGroupFilter(event.target.value)}
              onKeyDown={(event) => event.stopPropagation()}
            />
          </div>
          {groups
            .map((group, idx) => ({ group, idx }))
            .filter(({ group }) =>
              group.name.toLowerCase().includes(groupFilter.toLowerCase()),
            )
            .map(({ group, idx }) => (
              <MenuItem key={group.id} dense onClick={() => toggleGroup(idx)}>
                <Checkbox
                  size="small"
                  checked={selectedGroups.includes(idx)}
                  data-testid={`commentGroupCheckBox${group.id}`}
                />
                <ListItemText primary={group.name} />
              </MenuItem>
            ))}
        </Menu>
        {addComment && (
          <IconButton
            type="submit"
            color="primary"
            size="small"
            disabled={!textValue.trim()}
            name="submitCommentButton"
            data-testid="submitCommentButton"
          >
            <SendIcon fontSize="small" />
          </IconButton>
        )}
      </div>
    </form>
  );
};

export default CommentForm;
