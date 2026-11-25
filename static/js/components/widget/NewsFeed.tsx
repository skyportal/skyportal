import ReactMarkdown from "react-markdown";
import { Link as RouterLink } from "react-router-dom";

import Avatar from "@mui/material/Avatar";
import Box from "@mui/material/Box";
import Link from "@mui/material/Link";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import UserAvatar from "../user/UserAvatar";
import { rehypeEmoji } from "../comment/rehypeEmoji";
import {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
} from "../../ducks/profile";
import { useGetNewsFeedQuery } from "../../ducks/newsFeed";
import { useActiveTeam } from "../../ducks/teams";
import WidgetCard, { WidgetEmpty, muted } from "./WidgetCard";
import WidgetPrefsDialog from "./WidgetPrefsDialog";
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

const NewsFeedItem = ({ item }: { item: any }) => {
  const avatar =
    item.type === "source" ? (
      <Tooltip title="New source" arrow placement="top-start">
        <Avatar
          sx={{
            width: 32,
            height: 32,
            bgcolor: "primary.main",
            color: "primary.contrastText",
            fontSize: "0.8rem",
            fontWeight: 600,
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
    <Box
      data-testid="newsFeedItem"
      sx={{
        display: "flex",
        alignItems: "flex-start",
        gap: 1.5,
        py: 1,
        px: 1,
        mx: -1,
        borderRadius: 2,
        transition: "background-color 0.15s",
        "&:hover": { bgcolor: muted(0.05) },
      }}
    >
      <Box sx={{ flexShrink: 0, pt: 0.25 }}>{avatar}</Box>
      <Box sx={{ minWidth: 0, flex: 1 }}>
        <Box
          sx={{
            typography: "body2",
            "& p": { m: 0 },
            overflowWrap: "anywhere",
          }}
        >
          <ReactMarkdown rehypePlugins={[rehypeEmoji]}>
            {item.message.replace(
              /(?<!\w)([@#])([\w-@]+)/g,
              (_match: string, symbol: string, username: string) =>
                `***${symbol}${username}***`,
            )}
          </ReactMarkdown>
        </Box>
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ display: "flex", flexWrap: "wrap", columnGap: 0.75 }}
        >
          <Link
            component={RouterLink}
            to={`/source/${item.source_id}`}
            sx={{ fontWeight: 600 }}
          >
            {item.source_id}
          </Link>
          {item.classification && <span>{item.classification}</span>}
          <span>·</span>
          <span>{dayjs().to(dayjs.utc(`${item.time}Z`))}</span>
        </Typography>
      </Box>
    </Box>
  );
};

const NewsFeed = () => {
  const { activeTeam } = useActiveTeam();
  const { data: items, isLoading } = useGetNewsFeedQuery(
    activeTeam ? { teamID: activeTeam.id } : undefined,
  );
  const { data: profile } = useGetProfileQuery();
  const [updateUserPreferences] = useUpdateUserPreferencesMutation();
  const storedPrefs: any = profile?.preferences?.["newsFeed"] || defaultPrefs;
  const newsFeedPrefs = {
    ...storedPrefs,
    categories: {
      ...defaultPrefs.categories,
      ...(storedPrefs.categories || {}),
    },
  };

  return (
    <WidgetCard
      title="News feed"
      teamScoped
      actions={
        <WidgetPrefsDialog
          initialValues={newsFeedPrefs}
          stateBranchName="newsFeed"
          title="News feed"
          onSubmit={updateUserPreferences}
        />
      }
    >
      {isLoading ? (
        <WidgetLoading />
      ) : !items?.length ? (
        <WidgetEmpty>Nothing new.</WidgetEmpty>
      ) : (
        items.map((item: any) => (
          <NewsFeedItem
            key={`${item.author}-${item.source_id}-${item.time}`}
            item={item}
          />
        ))
      )}
    </WidgetCard>
  );
};

export default NewsFeed;
