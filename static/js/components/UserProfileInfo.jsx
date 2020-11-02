import React from "react";
import { useSelector } from "react-redux";

import Card from "@material-ui/core/Card";
import CardContent from "@material-ui/core/CardContent";
import Typography from "@material-ui/core/Typography";
import Box from "@material-ui/core/Box";
import Paper from "@material-ui/core/Paper";
import Grid from "@material-ui/core/Grid";
import PropTypes from "prop-types";

import md5 from "md5";

import { makeStyles } from "@material-ui/core/styles";

import UserAvatar from "./UserAvatar";

const useStyles = makeStyles({
  entryContent: {
    margin: "0.25rem",
  },
  card: {
    display: "inline-block",
  },
});

function gravatar_url(user) {
  const email = user.contact_email ? user.contact_email : user.username;
  const hash = md5(email);
  return `https://secure.gravatar.com/avatar/${hash}?d=blank`;
}

export const UserContactCard = ({ user }) => {
  const styles = useStyles();
  return (
    <Paper elevation={1} className={styles.card}>
      <div className={styles.entryContent}>
        <Grid container spacing={1} alignItems="center" justify="center">
          <Grid item xs={3}>
            <UserAvatar
              size={32}
              firstName={user.first_name}
              lastName={user.last_name}
              username={user.username}
              gravatarUrl={gravatar_url(user)}
            />
          </Grid>
          <Grid item xs={9}>
            {user.username} ({user.first_name} {user.last_name};
            {user.contact_email}; {user.contact_phone})
          </Grid>
        </Grid>
      </div>
    </Paper>
  );
};

UserContactCard.propTypes = {
  user: PropTypes.shape({
    first_name: PropTypes.string,
    last_name: PropTypes.string,
    username: PropTypes.string,
    contact_email: PropTypes.string,
    contact_phone: PropTypes.string,
  }).isRequired,
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
            {profile.first_name} {profile.last_name}
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
          {profile.acls?.length && (
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
