import React from "react";
import { useSelector } from "react-redux";

import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";
import PropTypes from "prop-types";

import UserAvatar, { isAllKoreanCharacters } from "./UserAvatar";

export const UserContactInfo = ({ user }) => {
  let contact_string = "";
  if (user.first_name || user.last_name) {
    contact_string += `${user.first_name} ${user.last_name} `;
  } else {
    contact_string += `${user.username} `;
  }

  const contact = [];
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

UserContactInfo.propTypes = {
  user: PropTypes.shape({
    first_name: PropTypes.string,
    last_name: PropTypes.string,
    username: PropTypes.string,
    contact_email: PropTypes.string,
    contact_phone: PropTypes.string,
  }).isRequired,
};

const getUserRealName = (firstName, lastName) => {
  // Korean names are generally written in last->first name order with no space in between
  if (isAllKoreanCharacters(firstName) && isAllKoreanCharacters(lastName)) {
    return `${lastName}${firstName}`;
  }
  return `${firstName} ${lastName}`;
};

const UserProfileInfo = () => {
  const profile = useSelector((state) => state.profile);

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
          />
          &nbsp;&nbsp;
          <h2
            id="userRealname"
            style={{
              visibility: !(profile.first_name || profile.last_name)
                ? "hidden"
                : "visible",
            }}
          >
            {(profile.first_name || profile.last_name) &&
              getUserRealName(profile.first_name, profile.last_name)}
          </h2>
        </div>
        &nbsp;
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
      </CardContent>
    </Card>
  );
};

export default UserProfileInfo;
