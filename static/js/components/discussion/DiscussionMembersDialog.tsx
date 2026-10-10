import { useState } from "react";
import { Link as RouterLink, useNavigate } from "react-router-dom";

import CloseIcon from "@mui/icons-material/Close";
import PersonAddIcon from "@mui/icons-material/PersonAddAlt1Outlined";
import PersonRemoveIcon from "@mui/icons-material/PersonRemoveOutlined";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import IconButton from "@mui/material/IconButton";
import Link from "@mui/material/Link";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";

import UserAvatar from "../user/UserAvatar";
import DiscussionAvatar from "./DiscussionAvatar";
import {
  Person,
  PersonRow,
  Row,
  SearchField,
  SectionLabel,
  matches,
  personName,
  usePeople,
} from "./people";
import { discussionTitle } from "./names";
import { useGetProfileQuery } from "../../ducks/profile";
import {
  Discussion,
  useAddDiscussionMembersMutation,
  useGetDiscussionMembersQuery,
  useRemoveDiscussionMemberMutation,
} from "../../ducks/discussions";

const SEARCH_FROM = 8;

interface DiscussionMembersDialogProps {
  discussion: Discussion;
  open: boolean;
  onClose: () => void;
}

const DiscussionMembersDialog = ({
  discussion,
  open,
  onClose,
}: DiscussionMembersDialogProps) => {
  const navigate = useNavigate();
  const myId = useGetProfileQuery().data?.id;
  const { data: members, isLoading } = useGetDiscussionMembersQuery(
    discussion.id,
    { skip: !open },
  );
  const { people } = usePeople();
  const [addMembers] = useAddDiscussionMembersMutation();
  const [removeMember] = useRemoveDiscussionMemberMutation();
  const [query, setQuery] = useState("");
  const [toAdd, setToAdd] = useState("");

  const editable = !discussion.group;
  const isCreator = discussion.creator_id === myId;
  const memberIds = new Set((members ?? []).map((member) => member.id));
  const shown = (members ?? []).filter((member) =>
    matches(query, member.username, member.first_name, member.last_name),
  );
  const addable = toAdd
    ? people.filter(
        (person) =>
          !memberIds.has(person.id) &&
          matches(toAdd, person.username, person.first_name, person.last_name),
      )
    : [];

  const openProfile = (person: Person) => {
    onClose();
    navigate(`/user/${person.id}`);
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      fullWidth
      maxWidth="sm"
      slotProps={{ paper: { sx: { borderRadius: 3, height: "80vh" } } }}
    >
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 1.5,
          padding: "1rem 1rem 0.75rem 1.25rem",
          borderBottom: 1,
          borderColor: "divider",
        }}
      >
        <DiscussionAvatar discussion={discussion} myId={myId} size={40} />
        <Box sx={{ flexGrow: 1, minWidth: 0 }}>
          <Typography variant="h6" noWrap sx={{ lineHeight: 1.3 }}>
            {discussionTitle(discussion, myId)}
          </Typography>
          <Typography variant="body2" color="textSecondary" noWrap>
            {discussion.group ? (
              <>
                Everyone in{" "}
                <Link
                  component={RouterLink}
                  to={`/group/${discussion.group.id}`}
                  onClick={onClose}
                >
                  {discussion.group.name}
                </Link>
                {`, ${discussion.member_count} members`}
              </>
            ) : (
              `${discussion.member_count} members`
            )}
          </Typography>
        </Box>
        <IconButton onClick={onClose}>
          <CloseIcon />
        </IconButton>
      </Box>
      <Box
        sx={{
          flexGrow: 1,
          minHeight: 0,
          overflowY: "auto",
          padding: "0.75rem 1rem 1rem",
        }}
      >
        {editable && (
          <>
            <SearchField
              value={toAdd}
              onChange={setToAdd}
              placeholder="Add people by name or username"
            />
            {addable.map((person) => (
              <PersonRow
                key={person.id}
                person={person}
                onClick={() => {
                  addMembers({ id: discussion.id, user_ids: [person.id] });
                  setToAdd("");
                }}
                end={<PersonAddIcon color="primary" />}
              />
            ))}
            {toAdd && addable.length === 0 && (
              <Typography
                variant="body2"
                color="textSecondary"
                sx={{ textAlign: "center", padding: 2 }}
              >
                Nobody else matches your search.
              </Typography>
            )}
          </>
        )}
        {!editable && (members?.length ?? 0) > SEARCH_FROM && (
          <SearchField
            value={query}
            onChange={setQuery}
            placeholder="Search members"
          />
        )}
        <SectionLabel>Members</SectionLabel>
        {isLoading && (
          <Box sx={{ display: "flex", justifyContent: "center", padding: 2 }}>
            <CircularProgress size={24} />
          </Box>
        )}
        {shown.map((member) => (
          <Row
            key={member.id}
            onClick={() => openProfile(member)}
            avatar={
              <UserAvatar
                size={40}
                firstName={member.first_name}
                lastName={member.last_name}
                username={member.username}
                gravatarUrl={member.gravatar_url ?? ""}
                isBot={member.is_bot}
                noTooltip
              />
            }
            primary={
              member.id === myId
                ? `${personName(member)} (you)`
                : personName(member)
            }
            secondary={
              member.id === discussion.creator_id && editable
                ? `@${member.username}, started the conversation`
                : `@${member.username}`
            }
            end={
              editable &&
              isCreator &&
              member.id !== myId && (
                <Tooltip title="Remove from the conversation">
                  <IconButton
                    onClick={(event) => {
                      event.stopPropagation();
                      removeMember({ id: discussion.id, userId: member.id });
                    }}
                    sx={{ "&:hover": { color: "error.main" } }}
                  >
                    <PersonRemoveIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              )
            }
          />
        ))}
      </Box>
    </Dialog>
  );
};

export default DiscussionMembersDialog;
