import ReactMarkdown from "react-markdown";
import { Link as RouterLink } from "react-router-dom";

import Avatar from "@mui/material/Avatar";
import Box from "@mui/material/Box";
import Link from "@mui/material/Link";
import Paper from "@mui/material/Paper";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import DragHandleIcon from "@mui/icons-material/DragHandle";
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
import { useActiveTeam } from "../../ducks/teams";
import WidgetLoading from "./WidgetLoading";

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

const emojiSupport = (text: any) =>
  text.value.replace(/:\w+:/gi, (name: string) => emoji.getUnicode(name));

const NewsFeedItem = ({ item }: { item: any }) => {
  const avatar =
    item.type === "source" ? (
      <Tooltip title="New source" arrow placement="top-start">
        <Avatar
          sx={{
            width: 32,
            height: 32,
            bgcolor: "#141b44",
            color: "white",
            fontSize: "0.75rem",
          }}
        >
          S
        </Avatar>
      </Tooltip>
    ) : (
      <UserAvatar
        size={32}
        userId={item.author_info.id}
        firstName={item.author_info.first_name}
        lastName={item.author_info.last_name}
        username={item.author_info.username}
        gravatarUrl={item.author_info.gravatar_url}
        isBot={item.author_info?.is_bot || false}
      />
    );

  return (
    <Paper
      variant="outlined"
      data-testid="newsFeedItem"
      sx={{
        display: "flex",
        alignItems: "center",
        gap: 1.5,
        p: 1,
        borderRadius: "8px",
        transition: "background-color 0.3s ease",
        "&:hover": { bgcolor: "action.hover" },
      }}
    >
      <Box sx={{ flexShrink: 0 }}>{avatar}</Box>
      <Box sx={{ minWidth: 0 }}>
        <Box sx={{ "& p": { m: 0 }, overflowWrap: "anywhere" }}>
          <ReactMarkdown components={{ text: emojiSupport } as any}>
            {item.message.replace(
              /(?<!\w)([@#])([\w-@]+)/g,
              (_match: string, symbol: string, username: string) =>
                `***${symbol}${username}***`,
            )}
          </ReactMarkdown>
        </Box>
        <Typography variant="caption" sx={{ color: "text.secondary" }}>
          <Link component={RouterLink} to={`/source/${item.source_id}`}>
            {item.source_id}
            {item.classification && ` (${item.classification})`}
          </Link>
          {" · "}
          <span>{dayjs().to(dayjs.utc(`${item.time}Z`))}</span>
        </Typography>
      </Box>
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
  const { activeTeam } = useActiveTeam();
  const { data: items, isLoading } = useGetNewsFeedQuery(
    activeTeam ? { teamID: activeTeam.id } : undefined,
  );
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
          <Typography
            variant="h6"
            sx={{
              display: "inline",
            }}
          >
            News Feed
            {activeTeam ? (
              <Typography
                component="span"
                sx={{
                  ml: 1,
                  px: 0.75,
                  py: 0.25,
                  borderRadius: "0.5rem",
                  fontSize: "0.7em",
                  color: "#fff",
                  backgroundColor: activeTeam.primary_color || "#457b9d",
                }}
              >
                {activeTeam.name}
              </Typography>
            ) : null}
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
        {isLoading && <WidgetLoading />}
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            gap: 1,
            overflowY: "auto",
            minHeight: 0,
            flex: 1,
            pt: 1,
          }}
        >
          {items?.map((item: any) => (
            <NewsFeedItem
              key={`${item.author}-${item.source_id}-${item.time}`}
              item={item}
            />
          ))}
        </Box>
      </div>
    </Paper>
  );
};

export default NewsFeed;
