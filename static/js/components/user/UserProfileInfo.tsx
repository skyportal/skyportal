import { useGetProfileQuery } from "../../ducks/profile";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";
import Tooltip from "@mui/material/Tooltip";
import Box from "@mui/material/Box";

import UserAvatar, { isAllKoreanCharacters } from "./UserAvatar";

interface UserContactInfoProps {
  user: {
    first_name?: string | null;
    last_name?: string | null;
    username?: string;
    contact_email?: string | null;
    contact_phone?: string | null;
    [key: string]: any;
  };
}

export const UserContactInfo = ({ user }: UserContactInfoProps) => {
  let contact_string = "";
  if (user.first_name || user.last_name) {
    contact_string += `${user.first_name} ${user.last_name} `;
  } else {
    contact_string += `${user.username} `;
  }

  const contact: string[] = [];
  if (user.contact_email) {
    contact.push(user.contact_email);
  }

  if (user.contact_phone) {
    contact.push(user.contact_phone);
  }

  if (contact.length > 0) {
    contact_string += `(${contact.join(";")})`;
  }
  return <p>{contact_string}</p>;
};

const getUserRealName = (firstName: any, lastName: any) => {
  // Korean names are generally written in last->first name order with no space in between
  if (isAllKoreanCharacters(firstName) && isAllKoreanCharacters(lastName)) {
    return `${lastName}${firstName}`;
  }
  return `${firstName} ${lastName}`;
};

const getUserAffiliations = (affiliations: string[]) => (
  <em>{affiliations.join(", ")}</em>
);

const UserProfileInfo = () => {
  const profile = useGetProfileQuery().data as any;

  return (
    <Card>
      <CardContent>
        <div
          style={{
            display: "flex",
            justifyContent: "flex-start",
            flexDirection: "row",
            alignItems: "center",
          }}
        >
          <UserAvatar
            size={128}
            firstName={profile.first_name}
            lastName={profile.last_name}
            username={profile.username}
            gravatarUrl={profile.gravatar_url}
            isBot={profile?.is_bot || false}
          />
          &nbsp;&nbsp;
          <div style={{ display: "flex", flexDirection: "column" }}>
            <h2
              id="userRealname"
              style={{
                visibility: !(profile.first_name || profile.last_name)
                  ? "hidden"
                  : "visible",
                margin: 0,
              }}
            >
              {(profile.first_name || profile.last_name) &&
                getUserRealName(profile.first_name, profile.last_name)}
            </h2>
            <h5
              id="userAffiliations"
              style={{
                visibility: !(profile?.affiliations?.length > 0)
                  ? "hidden"
                  : "visible",
                margin: 0,
              }}
            >
              {profile?.affiliations?.length > 0 &&
                getUserAffiliations(profile.affiliations)}
            </h5>
          </div>
        </div>
        &nbsp;
        {/* if the user has a bio, display it here in italic, full width */}
        {profile.bio && (
          <Typography
            component="div"
            style={{ width: "100%", display: "flex", flexWrap: "wrap" }}
          >
            <Box fontStyle="italic">{profile.bio}</Box>
          </Typography>
        )}
        <br />
        <Typography component="div">
          <Box pb={1}>
            <Box fontWeight="fontWeightBold" component="span" mr={1}>
              User roles:
            </Box>
            {profile.roles.join(", ")}
          </Box>
          {!!profile.acls?.length && (
            <Box pb={1}>
              <Box fontWeight="fontWeightBold" component="span" mr={1}>
                Additional user ACLs (separate from role-level ACLs):
              </Box>
              {profile.acls.join(", ")}
            </Box>
          )}
        </Typography>
        {profile.oauth_uid && (
          <Tooltip
            placement="bottom-start"
            title={
              <Typography variant="body2">
                This is the email address used to log in. Unlike the
                contact_email shown to other users, this cannot be edited. If
                you wish to change this, please contact a system administrator.
              </Typography>
            }
          >
            <Typography component="div">
              <Box pb={1}>
                <Box fontWeight="fontWeightBold" component="span" mr={1}>
                  Authentication email:
                </Box>
                {profile.oauth_uid}
              </Box>
            </Typography>
          </Tooltip>
        )}
      </CardContent>
    </Card>
  );
};

export default UserProfileInfo;
