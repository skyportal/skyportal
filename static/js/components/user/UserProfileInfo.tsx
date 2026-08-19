import { useGetProfileQuery } from "../../ducks/profile";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Tooltip from "@mui/material/Tooltip";
import Box from "@mui/material/Box";
import HelpOutlineOutlinedIcon from "@mui/icons-material/HelpOutlineOutlined";

import UserAvatar, { isAllKoreanCharacters } from "./UserAvatar";
import ThemeToggle from "./preferences/ThemeToggle";
import Chip from "@mui/material/Chip";

const getUserRealName = (firstName: any, lastName: any) => {
  // Korean names are generally written in last->first name order with no space in between
  if (isAllKoreanCharacters(firstName) && isAllKoreanCharacters(lastName)) {
    return `${lastName}${firstName}`;
  }
  return `${firstName} ${lastName}`;
};

const UserProfileInfo = () => {
  const profile = useGetProfileQuery().data as any;

  if (!profile) return <div data-testid="tour-profile-info" />;

  return (
    <Card data-testid="tour-profile-info">
      <CardContent
        style={{ display: "flex", flexDirection: "column", gap: "1rem" }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          <UserAvatar
            size={128}
            firstName={profile.first_name}
            lastName={profile.last_name}
            username={profile.username}
            gravatarUrl={profile.gravatar_url}
            isBot={profile?.is_bot || false}
          />
          <div>
            {(profile.first_name || profile.last_name) && (
              <h2 id="userRealname" style={{ margin: 0 }}>
                {getUserRealName(profile.first_name, profile.last_name)}
              </h2>
            )}
            {profile.affiliations?.length > 0 && (
              <h5 id="userAffiliations" style={{ margin: 0 }}>
                <em>{profile.affiliations.join(", ")}</em>
              </h5>
            )}
          </div>
          <Box sx={{ ml: "auto", alignSelf: "flex-start" }}>
            <ThemeToggle />
          </Box>
        </div>
        {profile.bio && <Box sx={{ fontStyle: "italic" }}>{profile.bio}</Box>}
        <Box>
          <b>User roles:</b> {profile.roles?.join(", ")}
        </Box>
        {!!profile.acls?.length && (
          <Box>
            <b>Additional user ACLs</b>
            <Tooltip title="Separate from role-level ACLs">
              <HelpOutlineOutlinedIcon
                fontSize="small"
                sx={{ verticalAlign: "text-bottom", mx: 0.3 }}
              />
            </Tooltip>
            :{" "}
            {profile.acls.map((acl: any) => (
              <Chip key={acl} label={acl} />
            ))}
          </Box>
        )}
        {profile.oauth_uid && (
          <Box>
            <b>Authentication email</b>
            <Tooltip
              title="This is the email address used to log in. Unlike the
              contact_email shown to other users, this cannot be edited. If
              you wish to change this, please contact a system administrator."
            >
              <HelpOutlineOutlinedIcon
                fontSize="small"
                sx={{ verticalAlign: "text-bottom", mx: 0.3 }}
              />
            </Tooltip>
            : {profile.oauth_uid}
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

export default UserProfileInfo;
