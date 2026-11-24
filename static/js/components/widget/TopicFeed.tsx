import { Link as RouterLink } from "react-router-dom";

import Box from "@mui/material/Box";
import Link from "@mui/material/Link";

import TopicFeedItem from "../topic/TopicFeedItem";
import {
  useGetTopicFeedInfiniteQuery,
  useGetTopicsQuery,
} from "../../ducks/topics";
import WidgetCard, { WidgetEmpty } from "./WidgetCard";
import WidgetLoading from "./WidgetLoading";

const TopicFeed = () => {
  const { data, isLoading } = useGetTopicFeedInfiniteQuery(null);
  const { data: topics } = useGetTopicsQuery();
  const items = data?.pages[0]?.items ?? [];
  const subscribed = topics?.some((topic) => topic.subscribed);

  return (
    <WidgetCard
      title={
        <Link component={RouterLink} to="/topics" color="inherit">
          Topics
        </Link>
      }
    >
      {isLoading ? (
        <WidgetLoading />
      ) : items.length === 0 ? (
        topics && (
          <WidgetEmpty>
            {subscribed ? (
              "Nothing new."
            ) : (
              <span>
                Subscribe to{" "}
                <Link component={RouterLink} to="/topics">
                  topics
                </Link>{" "}
                to follow them here.
              </span>
            )}
          </WidgetEmpty>
        )
      ) : (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
          {items.map((item) => (
            <TopicFeedItem
              key={`${item.type}-${item.id}`}
              item={item}
              topics={topics}
            />
          ))}
        </Box>
      )}
    </WidgetCard>
  );
};

export default TopicFeed;
