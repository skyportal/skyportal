import { ReactNode, useMemo, useState } from "react";

import AddCommentIcon from "@mui/icons-material/AddCommentOutlined";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import GroupAddIcon from "@mui/icons-material/GroupAddOutlined";
import GroupWorkIcon from "@mui/icons-material/GroupWork";
import GroupsIcon from "@mui/icons-material/Groups";
import Avatar from "@mui/material/Avatar";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { alpha } from "@mui/material/styles";

import Button from "../Button";
import UserAvatar from "../user/UserAvatar";
import {
  Person,
  PersonRow,
  Row,
  SearchField,
  SectionLabel,
  SelectMark,
  matches,
  personName,
  usePeople,
} from "./people";
import { otherMembers } from "./names";
import { Body, Empty, Header } from "./pane";
import { useGetGroupsQuery } from "../../ducks/groups";
import { useGetProfileQuery } from "../../ducks/profile";
import {
  useGetDiscussionsQuery,
  useStartDiscussionMutation,
} from "../../ducks/discussions";

export type NewKind = "direct" | "group";

interface NewDiscussionProps {
  onOpen: (id: number) => void;
  onBack?: (() => void) | undefined;
}

const NewDirectMessage = ({ onOpen, onBack }: NewDiscussionProps) => {
  const myId = useGetProfileQuery().data?.id;
  const { people, isLoading } = usePeople();
  const { data: discussions } = useGetDiscussionsQuery();
  const [startDiscussion, { isLoading: starting }] =
    useStartDiscussionMutation();
  const [query, setQuery] = useState("");

  const recentIds = useMemo(
    () =>
      (discussions ?? [])
        .filter((discussion) => discussion.is_direct)
        .map((discussion) => otherMembers(discussion, myId)[0]?.id)
        .filter((id): id is number => id !== undefined),
    [discussions, myId],
  );

  const open = (person: Person) => {
    if (starting) return;
    startDiscussion({ direct: true, user_ids: [person.id] })
      .unwrap()
      .then(({ id }) => onOpen(id))
      .catch(() => {});
  };

  const recent = query
    ? []
    : recentIds
        .map((id) => people.find((person) => person.id === id))
        .filter((person): person is Person => person !== undefined);
  const found = people.filter(
    (person) =>
      !recent.includes(person) &&
      matches(query, person.username, person.first_name, person.last_name),
  );

  const row = (person: Person) => (
    <PersonRow
      key={person.id}
      person={person}
      onClick={() => open(person)}
      end={<ChevronRightIcon sx={{ color: "action.active" }} />}
    />
  );

  return (
    <>
      <Header
        icon={<AddCommentIcon />}
        title="New direct message"
        subtitle="A private conversation with one person"
        onBack={onBack}
      />
      <Body>
        <SearchField
          autoFocus
          value={query}
          onChange={setQuery}
          placeholder="Search people by name or username"
        />
        {recent.length > 0 && (
          <>
            <SectionLabel>Recent</SectionLabel>
            {recent.map(row)}
          </>
        )}
        {found.length > 0 && (
          <SectionLabel>{query ? "Results" : "Everyone else"}</SectionLabel>
        )}
        {found.map(row)}
        {!isLoading && query && found.length === 0 && (
          <Empty>Nobody matches your search.</Empty>
        )}
      </Body>
    </>
  );
};

const ModeCard = ({
  icon,
  title,
  text,
  selected,
  onClick,
}: {
  icon: ReactNode;
  title: string;
  text: string;
  selected: boolean;
  onClick: () => void;
}) => (
  <Box
    role="button"
    tabIndex={0}
    onClick={onClick}
    onKeyDown={(event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        onClick();
      }
    }}
    sx={(theme) => ({
      flex: 1,
      minWidth: "14rem",
      display: "flex",
      gap: 1.5,
      padding: 1.5,
      borderRadius: 3,
      cursor: "pointer",
      border: 2,
      borderColor: selected ? "primary.main" : "divider",
      backgroundColor: selected
        ? alpha(theme.palette.primary.main, 0.08)
        : "background.paper",
      transition: "border-color 120ms, background-color 120ms",
      "&:hover, &:focus-visible": {
        borderColor: selected ? "primary.main" : "text.disabled",
        outline: "none",
      },
    })}
  >
    <Avatar
      sx={{
        width: 40,
        height: 40,
        bgcolor: selected ? "primary.main" : "action.selected",
        color: selected ? "primary.contrastText" : "text.secondary",
      }}
    >
      {icon}
    </Avatar>
    <Box sx={{ flexGrow: 1 }}>
      <Typography sx={{ fontWeight: 600 }}>{title}</Typography>
      <Typography variant="body2" color="textSecondary">
        {text}
      </Typography>
    </Box>
    <SelectMark selected={selected} />
  </Box>
);

const NewGroupConversation = ({ onOpen, onBack }: NewDiscussionProps) => {
  const { people, isLoading } = usePeople();
  const groups = (useGetGroupsQuery().data?.user ?? [])
    .filter((group) => !group["single_user_group"])
    .sort((a, b) => a.name.localeCompare(b.name));
  const [startDiscussion, { isLoading: starting }] =
    useStartDiscussionMutation();
  const [mode, setMode] = useState<"people" | "group">("people");
  const [name, setName] = useState("");
  const [query, setQuery] = useState("");
  const [picked, setPicked] = useState<Person[]>([]);
  const [groupId, setGroupId] = useState<number | null>(null);

  const group = groups.find((g) => g.id === groupId);
  const ready = mode === "people" ? picked.length > 0 : group !== undefined;

  const toggle = (person: Person) =>
    setPicked(
      picked.some((p) => p.id === person.id)
        ? picked.filter((p) => p.id !== person.id)
        : [...picked, person],
    );

  const create = () => {
    if (!ready || starting) return;
    const named = name.trim() || undefined;
    startDiscussion(
      mode === "people"
        ? { user_ids: picked.map((person) => person.id), name: named }
        : { group_id: groupId!, name: named },
    )
      .unwrap()
      .then(({ id }) => onOpen(id))
      .catch(() => {});
  };

  const foundPeople = people.filter((person) =>
    matches(query, person.username, person.first_name, person.last_name),
  );
  const foundGroups = groups.filter((g) => matches(query, g.name));

  return (
    <>
      <Header
        icon={<GroupAddIcon />}
        title="New group conversation"
        subtitle="Several people, or everyone in a group"
        onBack={onBack}
      />
      <Body>
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 2,
            marginBottom: 1,
          }}
        >
          <Avatar sx={{ width: 56, height: 56, bgcolor: "primary.main" }}>
            {mode === "group" ? <GroupWorkIcon /> : <GroupsIcon />}
          </Avatar>
          <TextField
            fullWidth
            variant="standard"
            placeholder={group ? group.name : "Name the conversation"}
            value={name}
            onChange={(event) => setName(event.target.value)}
            slotProps={{
              htmlInput: { maxLength: 200, "aria-label": "Conversation name" },
              input: { sx: { fontSize: "1.4rem", fontWeight: 500 } },
            }}
          />
        </Box>
        <SectionLabel>Who takes part</SectionLabel>
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1.5 }}>
          <ModeCard
            icon={<GroupsIcon />}
            title="Choose people"
            text="Pick the members. Anyone in it can add more later."
            selected={mode === "people"}
            onClick={() => setMode("people")}
          />
          <ModeCard
            icon={<GroupWorkIcon />}
            title="A whole group"
            text="Everyone in one of your groups, including future members."
            selected={mode === "group"}
            onClick={() => setMode("group")}
          />
        </Box>
        <Box sx={{ marginTop: 1.5 }}>
          <SearchField
            value={query}
            onChange={setQuery}
            placeholder={
              mode === "people" ? "Search people" : "Search your groups"
            }
          />
        </Box>
        {mode === "people" && picked.length > 0 && (
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, marginTop: 1 }}>
            {picked.map((person) => (
              <Chip
                key={person.id}
                label={personName(person)}
                onDelete={() => toggle(person)}
                avatar={
                  <UserAvatar
                    size={24}
                    firstName={person.first_name}
                    lastName={person.last_name}
                    username={person.username}
                    gravatarUrl={person.gravatar_url ?? ""}
                    noTooltip
                  />
                }
              />
            ))}
          </Box>
        )}
        {mode === "people" ? (
          <>
            <SectionLabel>{query ? "Results" : "People"}</SectionLabel>
            {foundPeople.map((person) => {
              const selected = picked.some((p) => p.id === person.id);
              return (
                <PersonRow
                  key={person.id}
                  person={person}
                  selected={selected}
                  onClick={() => toggle(person)}
                  end={<SelectMark selected={selected} />}
                />
              );
            })}
            {!isLoading && foundPeople.length === 0 && (
              <Empty>Nobody matches your search.</Empty>
            )}
          </>
        ) : (
          <>
            <SectionLabel>{query ? "Results" : "Your groups"}</SectionLabel>
            {foundGroups.map((g) => (
              <Row
                key={g.id}
                avatar={
                  <Avatar
                    sx={{ width: 40, height: 40, bgcolor: "primary.main" }}
                  >
                    <GroupWorkIcon fontSize="small" />
                  </Avatar>
                }
                primary={g.name}
                selected={g.id === groupId}
                onClick={() => setGroupId(g.id === groupId ? null : g.id)}
                end={<SelectMark selected={g.id === groupId} />}
              />
            ))}
            {foundGroups.length === 0 && (
              <Empty>
                {query
                  ? "No group matches your search."
                  : "You are not in any group yet."}
              </Empty>
            )}
          </>
        )}
      </Body>
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 2,
          padding: "0.75rem 1rem",
          borderTop: 1,
          borderColor: "divider",
        }}
      >
        <Typography
          variant="body2"
          color={ready ? "textSecondary" : "textDisabled"}
          noWrap
          sx={{ flexGrow: 1 }}
        >
          {mode === "people"
            ? picked.length
              ? `You and ${picked.length} ${picked.length === 1 ? "person" : "people"}`
              : "Pick at least one person"
            : group
              ? `Everyone in ${group.name}`
              : "Pick a group"}
        </Typography>
        <Button
          primary
          disabled={!ready || starting}
          onClick={create}
          data-testid="createGroupConversationButton"
          sx={{ flexShrink: 0, whiteSpace: "nowrap" }}
        >
          Create conversation
        </Button>
      </Box>
    </>
  );
};

const NewDiscussion = ({
  kind,
  ...props
}: NewDiscussionProps & { kind: NewKind }) => (
  <Box sx={{ display: "flex", flexDirection: "column", height: "100%" }}>
    {kind === "direct" ? (
      <NewDirectMessage {...props} />
    ) : (
      <NewGroupConversation {...props} />
    )}
  </Box>
);

export default NewDiscussion;
