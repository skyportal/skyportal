import { ReactNode, useMemo } from "react";

import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import RadioButtonUncheckedIcon from "@mui/icons-material/RadioButtonUnchecked";
import SearchIcon from "@mui/icons-material/Search";
import Box from "@mui/material/Box";
import InputAdornment from "@mui/material/InputAdornment";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import UserAvatar, { getUserRealName } from "../user/UserAvatar";
import { useGetProfileQuery } from "../../ducks/profile";
import { useGetUsersQuery } from "../../ducks/users";

export interface Person {
  id: number;
  username: string;
  first_name: string | null;
  last_name: string | null;
  gravatar_url: string | null;
  is_bot: boolean;
}

export const personName = (person: Person) =>
  getUserRealName(person.first_name, person.last_name) || person.username;

export const usePeople = () => {
  const myId = useGetProfileQuery().data?.id;
  const { data, isLoading } = useGetUsersQuery({ slim: true });
  const people = useMemo(
    () =>
      ((data?.users ?? []) as unknown as Person[])
        .filter((person) => !person.is_bot && person.id !== myId)
        .sort((a, b) => personName(a).localeCompare(personName(b))),
    [data, myId],
  );
  return { people, isLoading };
};

export const matches = (query: string, ...fields: (string | null)[]) => {
  const words = query.toLowerCase().split(/\s+/).filter(Boolean);
  const haystack = fields.join(" ").toLowerCase();
  return words.every((word) => haystack.includes(word));
};

export const SearchField = ({
  value,
  onChange,
  placeholder,
  autoFocus = false,
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  autoFocus?: boolean;
}) => (
  <TextField
    fullWidth
    autoFocus={autoFocus}
    placeholder={placeholder}
    value={value}
    onChange={(event) => onChange(event.target.value)}
    slotProps={{
      input: {
        sx: { borderRadius: 3, backgroundColor: "background.paper" },
        startAdornment: (
          <InputAdornment position="start">
            <SearchIcon />
          </InputAdornment>
        ),
      },
    }}
  />
);

export const SectionLabel = ({ children }: { children: ReactNode }) => (
  <Typography
    variant="overline"
    color="textSecondary"
    component="div"
    sx={{ padding: "0.75rem 0.75rem 0.25rem", lineHeight: 1.5 }}
  >
    {children}
  </Typography>
);

export const SelectMark = ({ selected }: { selected: boolean }) =>
  selected ? (
    <CheckCircleIcon color="primary" />
  ) : (
    <RadioButtonUncheckedIcon sx={{ color: "action.active" }} />
  );

interface RowProps {
  avatar: ReactNode;
  primary: ReactNode;
  secondary?: ReactNode;
  end?: ReactNode;
  selected?: boolean;
  onClick: () => void;
  testId?: string;
}

export const Row = ({
  avatar,
  primary,
  secondary,
  end,
  selected = false,
  onClick,
  testId,
}: RowProps) => (
  <Box
    role="button"
    tabIndex={0}
    data-testid={testId}
    onClick={onClick}
    onKeyDown={(event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        onClick();
      }
    }}
    sx={{
      display: "flex",
      alignItems: "center",
      gap: 1.5,
      padding: "0.5rem 0.75rem",
      borderRadius: 2,
      cursor: "pointer",
      backgroundColor: selected ? "action.selected" : "transparent",
      "&:hover, &:focus-visible": {
        backgroundColor: selected ? "action.selected" : "action.hover",
        outline: "none",
      },
    }}
  >
    {avatar}
    <Box sx={{ flexGrow: 1, minWidth: 0 }}>
      <Typography noWrap sx={{ fontWeight: 500 }}>
        {primary}
      </Typography>
      {secondary && (
        <Typography variant="body2" color="textSecondary" noWrap>
          {secondary}
        </Typography>
      )}
    </Box>
    {end}
  </Box>
);

export const PersonRow = ({
  person,
  end,
  selected,
  onClick,
}: {
  person: Person;
  end?: ReactNode;
  selected?: boolean;
  onClick: () => void;
}) => (
  <Row
    testId={`person-${person.username}`}
    avatar={
      <UserAvatar
        size={40}
        firstName={person.first_name}
        lastName={person.last_name}
        username={person.username}
        gravatarUrl={person.gravatar_url ?? ""}
        noTooltip
      />
    }
    primary={personName(person)}
    secondary={`@${person.username}`}
    end={end}
    selected={selected ?? false}
    onClick={onClick}
  />
);
