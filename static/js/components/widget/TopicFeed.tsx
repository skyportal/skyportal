import { Link as RouterLink } from "react-router-dom";

import Box from "@mui/material/Box";
import Link from "@mui/material/Link";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import DragHandleIcon from "@mui/icons-material/DragHandle";

import TopicFeedItem from "../topic/TopicFeedItem";
import {
  useGetTopicFeedInfiniteQuery,
  useGetTopicsQuery,
} from "../../ducks/topics";
import WidgetLoading from "./WidgetLoading";

interface TopicFeedProps {
  classes: {
    widgetPaperDiv: string;
    widgetIcon: string;
    widgetPaperFillSpace: string;
  };
}

const TopicFeed = ({ classes }: TopicFeedProps) => {
  const { data, isLoading } = useGetTopicFeedInfiniteQuery(null);
  const { data: topics } = useGetTopicsQuery();
  const items = data?.pages[0]?.items ?? [];
  const subscribed = topics?.some((topic) => topic.subscribed);

  return (
    <Paper elevation={1} className={classes.widgetPaperFillSpace}>
      <div className={classes.widgetPaperDiv}>
        <div>
          <Typography variant="h6" sx={{ display: "inline" }}>
            <Link component={RouterLink} to="/topics" color="inherit">
              Topics
            </Link>
          </Typography>
          <DragHandleIcon className={`${classes.widgetIcon} dragHandle`} />
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
            paddingTop: 1,
          }}
        >
          {!isLoading && items.length === 0 && topics && (
            <Typography variant="body2" color="textSecondary">
              {subscribed ? (
                "Nothing new."
              ) : (
                <>
                  Subscribe to{" "}
                  <Link component={RouterLink} to="/topics">
                    topics
                  </Link>{" "}
                  to follow them here.
                </>
              )}
            </Typography>
          )}
          {items.map((item) => (
            <TopicFeedItem
              key={`${item.type}-${item.id}`}
              item={item}
              topics={topics}
            />
          ))}
        </Box>
      </div>
    </Paper>
  );
};

export default TopicFeed;
