import React from 'react';
import PropTypes from 'prop-types';
import { createMuiTheme } from '@material-ui/core/styles';

import Avatar from '@material-ui/core/Avatar';

const theme = createMuiTheme({});

const UserAvatar = ({ size, firstName, lastName, username, gravatarUrl }) => {
  // use the hash of the username (which is in the gravatarUrl) to
  // select a unique color for this user
  function bgcolor() {
    let hash = gravatarUrl.split("/");
    hash = hash[hash.length - 1];
    if (hash.length >= 6) {
      // make the color string with a slight transparency
      return `#${hash.slice(0, 6)}aa`;
    } else {
      return '#aaaaaaaa';
    }
  }

  const usercolor = bgcolor();

  const backUpLetters = (firstName === null ? username.slice(0, 2) :`${firstName?.charAt(0)}${lastName?.charAt(0)}`);

  return (
    <Avatar
      alt={backUpLetters}
      src={`${gravatarUrl}s=${size}`}
      size={size}
      style={{
        width: size,
        height: size,
        backgroundColor: usercolor,
        color: theme.palette.getContrastText(usercolor),
        fontSize: `${Math.max(parseInt(parseFloat(size)/3, 10), 10)}px`
      }}
    >
      {backUpLetters}
    </Avatar>
  );
};

UserAvatar.propTypes = {
  size: PropTypes.number.isRequired,
  firstName: PropTypes.string,
  lastName: PropTypes.string,
  username: PropTypes.string.isRequired,
  gravatarUrl: PropTypes.string.isRequired
};

UserAvatar.defaultProps = {
  firstName: null,
  lastName: null
};

export default UserAvatar;
