import ReactMarkdown from "react-markdown";
import { Link as RouterLink } from "react-router-dom";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Link from "@mui/material/Link";
import Typography from "@mui/material/Typography";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";

import UserAvatar from "../user/UserAvatar";
import { rehypeEmoji } from "../comment/rehypeEmoji";
import { fromServer, userName } from "../discussion/names";
import type { Topic, TopicFeedItem as Item } from "../../ducks/topics";

dayjs.extend(relativeTime);

const ACTIONS: Record<Item["type"], (label: string | null) => string> = {
  post: () => "posted",
  classification: (label) => `classified as ${label}`,
  tag: (label) => `tagged ${label}`,
  comment: () => "commented on",
  spectrum: (label) => `added a ${label} spectrum to`,
};

interface TopicFeedItemProps {
  item: Item;
  topics?: Topic[] | undefined;
  onRemove?: (() => void) | undefined;
}

const TopicFeedItem = ({ item, topics, onRemove }: TopicFeedItemProps) => {
  const author = item.author;
  const itemTopics = topics?.filter((t) => item.topic_ids?.includes(t.id));
  return (
    <Box
      data-testid="topicFeedItem"
      sx={{
        display: "flex",
        gap: 1.5,
        padding: 1.25,
        borderRadius: 2,
        border: 1,
        borderColor: "divider",
        backgroundColor: "background.paper",
      }}
    >
      <Box sx={{ flexShrink: 0, paddingTop: 0.25 }}>
        {author && (
          <UserAvatar
            size={32}
            userId={author.id}
            firstName={author.first_name ?? null}
            lastName={author.last_name ?? null}
            username={author.username}
            gravatarUrl={author.gravatar_url ?? ""}
            isBot={author.is_bot ?? false}
          />
        )}
      </Box>
      <Box sx={{ flexGrow: 1, minWidth: 0 }}>
        <Typography variant="body2">
          <b>{author ? userName(author) : "Someone"}</b>{" "}
          {ACTIONS[item.type](item.label)}{" "}
          <Link
            component={RouterLink}
            to={`/source/${item.obj_id}`}
            sx={{ fontWeight: 600 }}
          >
            {item.obj_id}
          </Link>
        </Typography>
        {item.text && (
          <Box
            sx={{
              "& p": { margin: 0 },
              marginTop: 0.5,
              overflowWrap: "anywhere",
              color: "text.secondary",
              fontSize: "0.875rem",
            }}
          >
            <ReactMarkdown rehypePlugins={[rehypeEmoji]}>
              {item.text}
            </ReactMarkdown>
          </Box>
        )}
        <Box
          sx={{
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            gap: 0.75,
            marginTop: 0.75,
          }}
        >
          {itemTopics?.map((topic) => (
            <Chip
              key={topic.id}
              label={topic.name}
              size="small"
              component={RouterLink}
              to={`/topics?id=${topic.id}`}
              clickable
              sx={{ height: 20, fontSize: "0.7rem" }}
            />
          ))}
          <Typography variant="caption" color="textSecondary">
            {fromServer(item.time).fromNow()}
          </Typography>
          {onRemove && (
            <Button
              size="small"
              color="inherit"
              onClick={onRemove}
              sx={{
                marginLeft: "auto",
                minWidth: 0,
                padding: "0 0.25rem",
                fontSize: "0.75rem",
                color: "text.secondary",
              }}
            >
              Remove
            </Button>
          )}
        </Box>
      </Box>
    </Box>
  );
};

export default TopicFeedItem;
