import React from "react";
import { makeStyles } from "tss-react/mui";
import Avatar from "@mui/material/Avatar";
import Tooltip from "@mui/material/Tooltip";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import Badge from "@mui/material/Badge";

interface UserAvatarStyleParams {
  size: number;
  usercolor: string;
  backUpLetters: string;
}

const useStyles = makeStyles<UserAvatarStyleParams>()(
  (theme, { size, usercolor, backUpLetters }) => ({
    avatar: {
      width: size,
      height: size,
      backgroundColor: usercolor,
      "&:after": {
        content: `"${backUpLetters}"`,
        color: theme.palette.getContrastText(usercolor),
        fontWeight: "bold",
        fontSize: `${Math.max(parseInt(`${parseFloat(`${size}`) / 3}`, 10), 10)}px`,
        position: "absolute",
      },
    },
    avatarImg: {
      zIndex: 1,
    },
    badge: {
      fontSize: `${Math.max(parseInt(`${parseFloat(`${size}`) / 1.8}`, 10), 10)}px`,
      color: "#555555",
    },
  }),
);

// Return true if all characters in a string are Korean characters
export const isAllKoreanCharacters = (str: string) =>
  str.match(/^([가-힯]|[ᄀ-ᇿ]|[㄰-㆏]|[ꥠ-꥿]|[ힰ-퟿])+$/g);

const getInitials = (firstName: string | null, lastName: string | null) => {
  // Korean last names are almost always <=2 characters; last names are written first,
  // so using the full first name is a more natural "initials" than (firstName[0], lastName[0])
  // also, first names have more chance to be unique as a lot of last names are very common
  if (firstName && isAllKoreanCharacters(firstName)) {
    return firstName;
  }
  return `${firstName?.charAt(0)}${lastName?.charAt(0)}`;
};

interface UserAvatarProps {
  size: number;
  firstName?: string | null;
  lastName?: string | null;
  username: string;
  gravatarUrl: string;
  isBot?: boolean;
}

const UserAvatar = ({
  size,
  firstName = null,
  lastName = null,
  username,
  gravatarUrl,
  isBot = false,
}: UserAvatarProps) => {
  // use the hash of the username (which is in the gravatarUrl) to
  // select a unique color for this user
  function bgcolor() {
    let hash: any = gravatarUrl.split("/");
    hash = hash[hash.length - 1];
    if (hash.length >= 6) {
      // make the color string with a slight transparency
      return `#${hash.slice(0, 6)}aa`;
    }
    return "#aaaaaaaa";
  }

  const usercolor = bgcolor();

  const backUpLetters =
    firstName === null
      ? username.slice(0, 2)
      : getInitials(firstName, lastName);

  const props = { size, usercolor, backUpLetters };
  const { classes } = useStyles(props);

  let tooltipText = username;
  if (firstName && lastName) {
    tooltipText += ` (${firstName} ${lastName})`;
  }
  if (isBot) {
    tooltipText = `[Bot] ${tooltipText}`;
  }

  if (isBot) {
    return (
      <Tooltip title={tooltipText} arrow placement="top-start">
        <Badge
          overlap="circular"
          anchorOrigin={{ vertical: "top", horizontal: "right" }}
          badgeContent={
            <SmartToyIcon fontSize="small" className={classes.badge} />
          }
        >
          <Avatar
            alt={backUpLetters}
            src={`${gravatarUrl}&s=${size}`}
            classes={{
              root: classes.avatar,
              img: classes.avatarImg,
            }}
          />
        </Badge>
      </Tooltip>
    );
  }

  return (
    <Tooltip title={tooltipText} arrow placement="top-start">
      <Avatar
        alt={backUpLetters}
        src={`${gravatarUrl}&s=${size}`}
        classes={{
          root: classes.avatar,
          img: classes.avatarImg,
        }}
      />
    </Tooltip>
  );
};

export default UserAvatar;
