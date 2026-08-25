import { Link as RouterLink } from "react-router-dom";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { useGetProfileQuery } from "../../ducks/profile";
import { useGetGroupsQuery } from "../../ducks/groups";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Tooltip from "@mui/material/Tooltip";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import HelpOutlineOutlinedIcon from "@mui/icons-material/HelpOutlineOutlined";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";

import UserAvatar, { isAllKoreanCharacters } from "./UserAvatar";
import ThemeToggle from "./preferences/ThemeToggle";
import Chip from "@mui/material/Chip";
import Link from "@mui/material/Link";

dayjs.extend(utc);

export const getUserRealName = (firstName: any, lastName: any) => {
  // Korean names are generally written in last->first name order with no space in between
  if (
    isAllKoreanCharacters(firstName || "") &&
    isAllKoreanCharacters(lastName || "")
  ) {
    return `${lastName}${firstName}`;
  }
  return [firstName, lastName].filter(Boolean).join(" ");
};

const UserProfileInfo = () => {
  const profile = useGetProfileQuery().data as any;
  const groups = useGetGroupsQuery().data?.user;

  if (!profile) return <div data-testid="tour-profile-info" />;

  const groupNames = (groups ?? [])
    .filter((group) => !group["single_user_group"])
    .map((group) => group.name)
    .sort();

  const field = (label: any, value: any) => (
    <Typography variant="body2">
      <b>{label}:</b> {value}
    </Typography>
  );

  const chips = (values: string[]) => (
    <Box
      component="span"
      sx={{ display: "inline-flex", flexWrap: "wrap", gap: 0.5 }}
    >
      {values.map((value) => (
        <Chip key={value} label={value} size="small" />
      ))}
    </Box>
  );

  const helpIcon = (title: string) => (
    <Tooltip title={title}>
      <HelpOutlineOutlinedIcon
        fontSize="small"
        sx={{ verticalAlign: "text-bottom", mx: 0.3 }}
      />
    </Tooltip>
  );

  return (
    <Card data-testid="tour-profile-info">
      <CardContent>
        <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
          <UserAvatar
            size={128}
            firstName={profile.first_name}
            lastName={profile.last_name}
            username={profile.username}
            gravatarUrl={profile.gravatar_url}
            isBot={profile?.is_bot || false}
          />
          <div>
            <Typography variant="h5" id="userRealname">
              {getUserRealName(profile.first_name, profile.last_name)}
            </Typography>
            <Typography variant="subtitle1" color="textSecondary">
              @{profile.username}
            </Typography>
            {!!profile.affiliations?.length && (
              <Typography variant="body2" id="userAffiliations">
                <em>{profile.affiliations.join(", ")}</em>
              </Typography>
            )}
          </div>
          <Box sx={{ ml: "auto", alignSelf: "flex-start" }}>
            <ThemeToggle />
          </Box>
        </Box>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 1, mt: 2 }}>
          {profile.bio && (
            <Typography variant="body2" color="textSecondary">
              {profile.bio}
            </Typography>
          )}
          {profile.contact_email &&
            field(
              "Contact email",
              <Link href={`mailto:${profile.contact_email}`}>
                {profile.contact_email}
              </Link>,
            )}
          {profile.contact_phone &&
            field("Contact phone", profile.contact_phone)}
          {field(
            "Member since",
            dayjs.utc(`${profile.created_at}Z`).format("MMMM D, YYYY"),
          )}
          {!!profile.roles?.length && field("Roles", chips(profile.roles))}
          {!!groupNames.length && field("Groups", chips(groupNames))}
          {!!profile.acls?.length &&
            field(
              <>
                Additional user ACLs
                {helpIcon("Separate from role-level ACLs")}
              </>,
              chips(profile.acls),
            )}
          {profile.oauth_uid &&
            field(
              <>
                Authentication email
                {helpIcon(
                  "This is the email address used to log in. Unlike the contact_email shown to other users, this cannot be edited. If you wish to change this, please contact a system administrator.",
                )}
              </>,
              profile.oauth_uid,
            )}
          <Link
            component={RouterLink}
            to={`/user/${profile.id}`}
            data-testid="profile-public-view"
            variant="body2"
            sx={{
              alignSelf: "flex-start",
              display: "flex",
              alignItems: "center",
              gap: 0.5,
            }}
          >
            View public profile
            <OpenInNewIcon fontSize="inherit" />
          </Link>
        </Box>
      </CardContent>
    </Card>
  );
};

export default UserProfileInfo;
