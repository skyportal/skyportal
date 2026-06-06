import ReactMarkdown from "react-markdown";
import { Link } from "react-router-dom";

import Avatar from "@mui/material/Avatar";
import Paper from "@mui/material/Paper";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import DragHandleIcon from "@mui/icons-material/DragHandle";
import { makeStyles } from "tss-react/mui";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";
import emoji from "emoji-dictionary";

import WidgetPrefsDialog from "./WidgetPrefsDialog";
import UserAvatar from "../user/UserAvatar";
import {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
} from "../../ducks/profile";
import { useGetNewsFeedQuery } from "../../ducks/newsFeed";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const defaultPrefs = {
  numItems: "10",
  categories: {
    classifications: true,
    comments: true,
    photometry: true,
    sources: true,
    spectra: true,
    includeCommentsFromBots: false,
  },
};

const useStyles = makeStyles()((theme) => ({
  newsFeed: {
    display: "flex",
    flexDirection: "column",
    overflowY: "scroll",
    paddingLeft: "0.3125rem",
    backgroundColor: theme.palette.background.default,
  },
  entry: {
    display: "flex",
    flexDirection: "row",
    padding: "0.3125rem 0.625rem 0.625rem 0.3125rem",
    marginBottom: "0.625rem",
    marginRight: "0.3125rem",
    alignItems: "center",
  },
  entryMessage: {
    maxWidth: "350px",
    marginBottom: "0.2em",
    "& > p": {
      margin: 0,
    },
  },
  entryContent: {
    paddingTop: "0.3em",
    paddingBottom: "0.1em",
    display: "flex",
    flexDirection: "column",
  },
  entryAvatar: {
    marginRight: "0.6em",
  },
  entryIdent: {
    display: "flex",
    flexDirection: "row",
    alignItems: "baseline",
    color: "#aaa",
    fontSize: "80%",
  },
  entryTime: {
    marginLeft: "0.5em",
  },
  entrySourceId: {
    marginRight: "0.5em",
    fontSize: "105%",
    "& > a": {
      color: "#9b9a9a !important",
    },
  },
  entryTitle: {
    fontSize: "0.875em !important",
    padding: "0.3125rem 0.625rem !important",
  },
}));

interface NewsFeedItemProps {
  item: any;
}

const NewsFeedItem = ({ item }: NewsFeedItemProps) => {
  const { classes: styles } = useStyles();
  const emojiSupport = (text: any) =>
    text.value.replace(/:\w+:/gi, (name: string) => emoji.getUnicode(name));

  let entryAvatar = null;
  let entryTitle;
  // Use switch-case to make it easy to add future newsfeed types
  switch (item.type) {
    case "comment":
    case "photometry":
    case "spectrum":
    case "classification":
      entryAvatar = (
        <UserAvatar
          size={32}
          firstName={item.author_info.first_name}
          lastName={item.author_info.last_name}
          username={item.author_info.username}
          gravatarUrl={item.author_info.gravatar_url}
          isBot={item.author_info?.is_bot || false}
        />
      );
      entryTitle = null;
      break;
    case "source":
      entryAvatar = (
        <Avatar
          alt="S"
          style={{
            width: 32,
            height: 32,
            backgroundColor: "#141b44",
            color: "white",
            fontSize: "10px",
          }}
        >
          S
        </Avatar>
      );

      entryTitle = "New source";
      break;
    default:
      break;
  }

  return (
    <Paper
      key={`newsFeedItem_${item.time}`}
      className={styles.entry}
      elevation={1}
    >
      {entryTitle !== null ? (
        <Tooltip
          title={entryTitle}
          arrow
          placement="top-start"
          classes={{ tooltip: styles.entryTitle }}
        >
          <div className={styles.entryAvatar}>{entryAvatar}</div>
        </Tooltip>
      ) : (
        <div className={styles.entryAvatar}>{entryAvatar}</div>
      )}
      <div className={styles.entryContent}>
        <ReactMarkdown
          className={styles.entryMessage}
          components={{ text: emojiSupport } as any}
        >
          {item.message.replace(
            /(?<!\w)([@#])([\w-@]+)/g,
            (_match: string, symbol: string, username: string) => {
              return `***${symbol}${username}***`;
            },
          )}
        </ReactMarkdown>
        <div className={styles.entryIdent}>
          <span className={styles.entrySourceId}>
            <Link to={`/source/${item.source_id}`}>
              {item?.classification ? (
                <div>
                  Source: {item.source_id} ({item.classification})
                </div>
              ) : (
                <div>Source: {item.source_id}</div>
              )}
            </Link>
          </span>
          <span> &#124; </span>
          <span className={styles.entryTime}>
            {dayjs().to(dayjs.utc(`${item.time}Z`))}
          </span>
        </div>
      </div>
    </Paper>
  );
};

interface NewsFeedProps {
  classes: {
    widgetPaperDiv: string;
    widgetIcon: string;
    widgetPaperFillSpace: string;
  };
}

const NewsFeed = ({ classes }: NewsFeedProps) => {
  const { classes: styles } = useStyles();
  const { data: items } = useGetNewsFeedQuery();
  const { data: profile } = useGetProfileQuery();
  const [updateUserPreferences] = useUpdateUserPreferencesMutation();
  const rawNewsFeedPrefs: any =
    profile?.preferences?.["newsFeed"] || defaultPrefs;
  const newsFeedPrefs = {
    ...rawNewsFeedPrefs,
    categories: {
      ...defaultPrefs.categories,
      ...(rawNewsFeedPrefs.categories || {}),
    },
  };

  return (
    <Paper elevation={1} className={classes.widgetPaperFillSpace}>
      <div className={classes.widgetPaperDiv}>
        <div>
          <Typography variant="h6" display="inline">
            News Feed
          </Typography>
          <DragHandleIcon className={`${classes.widgetIcon} dragHandle`} />
          <div className={classes.widgetIcon}>
            <WidgetPrefsDialog
              initialValues={newsFeedPrefs}
              stateBranchName="newsFeed"
              title="News Feed Preferences"
              onSubmit={updateUserPreferences}
            />
          </div>
        </div>
        <div
          className={styles.newsFeed}
          style={{
            height: "calc(100% - 2.5rem)",
            overflowY: "auto",
            paddingTop: "0.1rem",
          }}
        >
          {items?.map((item: any) => (
            <NewsFeedItem
              key={`${item.author}-${item.source_id}-${item.time}`}
              item={item}
            />
          ))}
        </div>
      </div>
    </Paper>
  );
};

export default NewsFeed;
