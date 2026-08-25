import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Link from "@mui/material/Link";
import Typography from "@mui/material/Typography";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import { Link as RouterLink } from "react-router-dom";

import Button from "../Button";
import Paper from "../Paper";
import Spinner from "../Spinner";
import UserAvatar from "./UserAvatar";
import withRouter from "../withRouter";
import { getUserRealName } from "./UserProfileInfo";
import { useGetProfileQuery } from "../../ducks/profile";
import { useGetUserPublicProfileQuery } from "../../ducks/users";

dayjs.extend(utc);

interface PublicProfileProps {
  route?: { id: string } | undefined;
}

const PublicProfile = ({ route }: PublicProfileProps) => {
  const id = route?.id;
  const { data: profile, isError } = useGetUserPublicProfileQuery(id!, {
    skip: !id,
  });
  const currentUserId = useGetProfileQuery().data?.id;

  if (isError) return <div>Cannot find this user.</div>;
  if (!profile) return <Spinner />;

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

  return (
    <>
      {String(currentUserId) === String(id) && (
        <Button
          secondary
          size="small"
          component={RouterLink}
          to="/profile"
          data-testid="profile-settings-view"
          sx={{ mb: 0.5 }}
        >
          <ArrowBackIcon fontSize="small" sx={{ mr: 0.5 }} />
          settings
        </Button>
      )}
      <Paper>
        <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
          <UserAvatar
            size={128}
            firstName={profile.first_name}
            lastName={profile.last_name}
            username={profile.username}
            gravatarUrl={profile.gravatar_url}
            isBot={profile.is_bot}
            noTooltip
          />
          <div>
            <Typography variant="h5" id="publicProfileRealname">
              {getUserRealName(profile.first_name, profile.last_name)}
            </Typography>
            <Typography variant="subtitle1" color="textSecondary">
              @{profile.username}
            </Typography>
            {!!profile.affiliations?.length && (
              <Typography variant="body2">
                <em>{profile.affiliations.join(", ")}</em>
              </Typography>
            )}
          </div>
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
          {!!profile.roles?.length && field("Roles", chips(profile.roles))}
          {!!profile.groups?.length && field("Groups", chips(profile.groups))}
          {field(
            "Member since",
            dayjs.utc(`${profile.created_at}Z`).format("MMMM D, YYYY"),
          )}
        </Box>
      </Paper>
    </>
  );
};

export default withRouter(PublicProfile);
