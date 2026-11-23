import { useEffect, useMemo, useRef, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import ArrowUpwardIcon from "@mui/icons-material/ArrowUpward";
import AttachFileIcon from "@mui/icons-material/AttachFile";
import CheckIcon from "@mui/icons-material/Check";
import GroupIcon from "@mui/icons-material/Group";
import Box from "@mui/material/Box";
import Checkbox from "@mui/material/Checkbox";
import IconButton from "@mui/material/IconButton";
import ListItemText from "@mui/material/ListItemText";
import ListSubheader from "@mui/material/ListSubheader";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";

import { useGetConfigQuery } from "../../ducks/config";
import { useGetGroupsQuery } from "../../ducks/groups";
import { useGetProfileQuery } from "../../ducks/profile";
import Button from "../Button";
import SegmentedControl from "../SegmentedControl";
import { composerSx, sendButtonSx } from "./chatStyles";

import UsernameTrie from "../../usernameTrie";
import InstrumentTrie from "../../instrumentTrie";
import { useGetInstrumentsQuery } from "../../ducks/instruments";
import { useGetUsersQuery } from "../../ducks/users";

const suggestionListSx = { overflowY: "auto", maxHeight: "10rem" } as const;

const suggestionButtonSx = {
  justifyContent: "flex-start",
  width: "100%",
  textTransform: "none",
  fontWeight: 400,
  borderRadius: "8px",
  color: "text.primary",
} as const;

const menuSectionSx = { lineHeight: "2rem", top: "3.25rem" } as const;

interface CommentComposerProps {
  addComment?: ((...a: any[]) => void) | null;
  editComment?: ((...a: any[]) => void) | null;
  commentText?: string;
  attachmentName?: string;
  onClose?: (() => void) | null;
  placeholder?: string;
  textOnly?: boolean;
  streamAccess?: boolean;
}

const CommentForm = ({
  addComment = null,
  editComment = null,
  commentText = "",
  attachmentName = "",
  onClose = null,
  placeholder = "Add a comment",
  textOnly = false,
  streamAccess = false,
}: CommentComposerProps) => {
  // Only usernames are needed, for the @-mention trie.
  const users = useGetUsersQuery({ slim: true }).data ?? { users: [] };
  const { data: groupsData } = useGetGroupsQuery();
  const groups = useMemo(() => groupsData?.userAccessible ?? [], [groupsData]);
  const config = useGetConfigQuery().data as any;
  const publicGroup: any = groups.find(
    (group) => group.name === config?.publicGroupName,
  );
  const { data: profile } = useGetProfileQuery();
  const streams: any[] = streamAccess
    ? (profile?.streams ?? []).filter(
        (stream: any) =>
          !publicGroup?.streams?.some((s: any) => s.id === stream.id),
      )
    : [];
  const [selectedStreams, setSelectedStreams] = useState<number[]>([]);
  const [showPublic, setShowPublic] = useState(false);
  const [publicText, setPublicText] = useState("");
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
    if (selectedStreams.length) {
      data.stream_ids = selectedStreams;
      if (publicText.trim()) {
        data.public_text = publicText;
      }
    }
    if (addComment) {
      addComment(data);
    } else if (editComment) {
      editComment(data);
    }
    reset();
    setTextValue("");
    setFileName("");
    setSelectedGroups([]);
    setSelectedStreams([]);
    setPublicText("");
    setShowPublic(false);
    setGroupFilter("");
    setAutosuggestVisible(false);
    setUsernamePrefixMatches({});
    onClose?.();
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
    } else if (event.key === "Escape" && isEdit) {
      event.preventDefault();
      onClose?.();
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
    <Box
      sx={[
        {
          display: autosuggestVisible ? "block" : "none",
          padding: "0.25rem",
          "& li": { listStyle: "none" },
        },
        Boolean(addComment) &&
          ((theme) => ({
            position: "absolute",
            bottom: "100%",
            left: "0.75rem",
            right: "0.75rem",
            zIndex: 1,
            borderRadius: "12px",
            border: `1px solid ${theme.palette.divider}`,
            backgroundColor: theme.palette.background.paper,
            boxShadow: theme.shadows[4],
          })),
      ]}
    >
      <Box sx={suggestionListSx}>
        {Object.entries(usernamePrefixMatches).map(
          ([username, { firstName, lastName }]: [string, any], ix) => (
            <li key={username}>
              <Button
                onClick={() => handleClickSuggestedUsername(username)}
                sx={suggestionButtonSx}
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
      </Box>
      <Box sx={suggestionListSx}>
        {Object.entries(instrumentPrefixMatches).map(
          ([instrument, { telescope }]: [string, any], ix) => (
            <li key={instrument}>
              <Button
                onClick={() => handleClickSuggestedInstrument(instrument)}
                sx={suggestionButtonSx}
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
      </Box>
    </Box>
  );

  const editingPublic = showPublic && selectedStreams.length > 0;
  const textError = !editingPublic && !!errors["text"];
  const extrasSx = {
    display: "flex",
    flexWrap: "wrap",
    alignItems: "center",
    padding: isEdit ? "0 0 0.25rem" : "0 1.5rem 0.25rem",
  } as const;

  return (
    <Box
      component="form"
      onSubmit={handleSubmit(onSubmit)}
      data-testid="comment-form"
      sx={{
        position: "relative",
        padding: isEdit ? 0 : "0.5rem 0.75rem 0.75rem",
      }}
    >
      {suggestions}
      {(fileName || attachmentName) && (
        <Box sx={extrasSx}>
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
        </Box>
      )}
      {selectedStreams.length > 0 && (
        <Box sx={extrasSx}>
          <SegmentedControl
            size="small"
            value={editingPublic ? "public" : "private"}
            options={[
              { value: "private", label: "Private" },
              { value: "public", label: "Public" },
            ]}
            onChange={(version) => setShowPublic(version === "public")}
          />
        </Box>
      )}
      <Box sx={(theme) => composerSx(theme, textError)}>
        <Controller
          render={() => (
            <TextField
              id="root_comment"
              autoFocus={isEdit}
              value={editingPublic ? publicText : textValue}
              onChange={
                editingPublic
                  ? (event) => setPublicText(event.target.value)
                  : handleTextInputChange
              }
              placeholder={
                editComment
                  ? "Edit comment"
                  : editingPublic
                    ? "Public version"
                    : placeholder
              }
              name="text"
              error={textError}
              variant="standard"
              fullWidth
              multiline
              maxRows={6}
              inputRef={textAreaRef}
              onKeyDown={handleComposerKeyDown}
              slotProps={{ input: { disableUnderline: true } }}
              sx={{
                alignSelf: "center",
                "& .MuiInputBase-root": { fontSize: "0.875rem" },
              }}
            />
          )}
          name="text"
          control={control}
          rules={{ required: textRequired }}
        />
        {!textOnly && (
          <>
            <Tooltip title="Attachment">
              <IconButton
                component="label"
                size="small"
                sx={{ color: "text.secondary" }}
              >
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
                selectedGroups.length || selectedStreams.length
                  ? [
                      selectedGroups.length &&
                        `Shared with ${selectedGroups.length} group(s)`,
                      selectedStreams.length &&
                        `visible to ${selectedStreams.length} stream(s)`,
                    ]
                      .filter(Boolean)
                      .join(", ")
                  : "Customize group access (public if not specified)"
              }
            >
              <IconButton
                size="small"
                sx={{
                  color:
                    selectedGroups.length || selectedStreams.length
                      ? "primary.main"
                      : "text.secondary",
                }}
                onClick={(event) => setGroupAnchor(event.currentTarget)}
                data-testid="customizeGroupsButton"
              >
                <GroupIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          </>
        )}
        <Menu
          anchorEl={groupAnchor}
          open={Boolean(groupAnchor)}
          onClose={() => setGroupAnchor(null)}
          slotProps={{
            paper: {
              sx: { maxHeight: "20rem", width: "18rem", borderRadius: "12px" },
            },
          }}
        >
          <Box
            sx={{
              position: "sticky",
              top: 0,
              zIndex: 2,
              padding: "0.25rem 0.5rem 0.5rem",
              backgroundColor: "background.paper",
            }}
          >
            <TextField
              autoFocus
              fullWidth
              size="small"
              placeholder="Visible only to"
              value={groupFilter}
              onChange={(event) => setGroupFilter(event.target.value)}
              onKeyDown={(event) => event.stopPropagation()}
            />
          </Box>
          {streams.length > 0 && (
            <ListSubheader sx={menuSectionSx}>Streams</ListSubheader>
          )}
          {streams
            .filter((stream: any) =>
              stream.name.toLowerCase().includes(groupFilter.toLowerCase()),
            )
            .map((stream: any) => (
              <MenuItem
                key={`stream-${stream.id}`}
                dense
                onClick={() =>
                  setSelectedStreams(
                    selectedStreams.includes(stream.id)
                      ? selectedStreams.filter((id) => id !== stream.id)
                      : [...selectedStreams, stream.id],
                  )
                }
              >
                <Checkbox
                  size="small"
                  checked={selectedStreams.includes(stream.id)}
                  data-testid={`commentStreamCheckBox${stream.id}`}
                />
                <ListItemText primary={stream.name} />
              </MenuItem>
            ))}
          {streams.length > 0 && (
            <ListSubheader sx={menuSectionSx}>Groups</ListSubheader>
          )}
          {groups
            .map((group, idx) => ({ group, idx }))
            .filter(
              ({ group }) =>
                group.id !== publicGroup?.id &&
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
        <IconButton
          type="submit"
          size="small"
          disabled={isAdd && !textValue.trim()}
          name={isEdit ? "editCommentSubmitButton" : "submitCommentButton"}
          data-testid={
            isEdit ? "editCommentSubmitButton" : "submitCommentButton"
          }
          sx={sendButtonSx}
        >
          {isEdit ? (
            <CheckIcon sx={{ fontSize: "1.1rem" }} />
          ) : (
            <ArrowUpwardIcon sx={{ fontSize: "1.1rem" }} />
          )}
        </IconButton>
      </Box>
    </Box>
  );
};

export default CommentForm;
