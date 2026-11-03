import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import useMediaQuery from "@mui/material/useMediaQuery";

import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import { Body, Empty } from "../discussion/pane";
import { userName } from "../discussion/names";
import TopicDialog from "./TopicDialog";
import TopicFeedItem from "./TopicFeedItem";
import { useGetProfileQuery } from "../../ducks/profile";
import {
  Topic,
  useDeleteTopicMutation,
  useGetTopicFeedInfiniteQuery,
  useGetTopicsQuery,
  usePostTopicSourceMutation,
  useRemoveTopicSourceMutation,
  useSubscribeToTopicMutation,
  useUnsubscribeFromTopicMutation,
} from "../../ducks/topics";

const plural = (count: number, word: string) =>
  `${count} ${word}${count === 1 ? "" : "s"}`;

const PostSourceForm = ({ topic }: { topic: Topic }) => {
  const [postTopicSource, { isLoading }] = usePostTopicSourceMutation();
  const [objId, setObjId] = useState("");
  const [text, setText] = useState("");

  const post = async () => {
    const result = await postTopicSource({
      id: topic.id,
      obj_id: objId.trim(),
      text: text.trim(),
    });
    if (!result.error) {
      setObjId("");
      setText("");
    }
  };

  return (
    <Box
      component="form"
      onSubmit={(event) => {
        event.preventDefault();
        post();
      }}
      sx={{ display: "flex", flexWrap: "wrap", gap: 1, alignItems: "center" }}
    >
      <TextField
        size="small"
        placeholder="Source ID"
        value={objId}
        onChange={(event) => setObjId(event.target.value)}
        sx={{ width: "11rem" }}
        data-testid="topicSourceInput"
      />
      <TextField
        size="small"
        placeholder="Why it belongs here"
        value={text}
        onChange={(event) => setText(event.target.value)}
        sx={{ flexGrow: 1, minWidth: "12rem" }}
        slotProps={{ htmlInput: { maxLength: 2000 } }}
      />
      <Button
        type="submit"
        variant="contained"
        disabled={!objId.trim() || isLoading}
        data-testid="postTopicSourceButton"
      >
        Post
      </Button>
    </Box>
  );
};

const TopicPane = ({
  topic,
  canEdit,
  myId,
  onEdit,
  onDeleted,
  onBack,
}: {
  topic: Topic;
  canEdit: boolean;
  myId: number | undefined;
  onEdit: () => void;
  onDeleted: () => void;
  onBack?: (() => void) | undefined;
}) => {
  const { data, isLoading, hasNextPage, fetchNextPage, isFetchingNextPage } =
    useGetTopicFeedInfiniteQuery(topic.id);
  const [subscribe, { isLoading: subscribing }] = useSubscribeToTopicMutation();
  const [unsubscribe, { isLoading: unsubscribing }] =
    useUnsubscribeFromTopicMutation();
  const [deleteTopic] = useDeleteTopicMutation();
  const [removeTopicSource] = useRemoveTopicSourceMutation();
  const [confirmDelete, setConfirmDelete] = useState(false);
  const items = data?.pages.flatMap((page) => page.items ?? []) ?? [];

  return (
    <Box sx={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <Body>
        <Box sx={{ display: "flex", alignItems: "flex-start", gap: 2 }}>
          {onBack && (
            <IconButton size="small" onClick={onBack} sx={{ marginTop: 0.5 }}>
              <ArrowBackIcon fontSize="small" />
            </IconButton>
          )}
          <Box sx={{ flexGrow: 1, minWidth: 0 }}>
            <Typography variant="h5" sx={{ fontWeight: 600 }}>
              {topic.name}
            </Typography>
            <Typography variant="body2" color="textSecondary">
              {plural(topic.subscriber_count, "subscriber")}
              {topic.creator && ` · created by ${userName(topic.creator)}`}
            </Typography>
          </Box>
          <Button
            variant={topic.subscribed ? "outlined" : "contained"}
            disabled={subscribing || unsubscribing}
            onClick={() =>
              topic.subscribed ? unsubscribe(topic.id) : subscribe(topic.id)
            }
            sx={{ flexShrink: 0 }}
            data-testid="topicSubscribeButton"
          >
            {topic.subscribed ? "Unsubscribe" : "Subscribe"}
          </Button>
        </Box>
        {topic.description && (
          <Typography sx={{ whiteSpace: "pre-wrap" }}>
            {topic.description}
          </Typography>
        )}
        {Boolean(topic.classifications?.length || topic.tags?.length) && (
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75 }}>
            {topic.classifications?.map((classification) => (
              <Chip
                key={classification}
                label={classification}
                size="small"
                variant="outlined"
              />
            ))}
            {topic.tags?.map((tag) => (
              <Chip
                key={tag.id}
                label={tag.name}
                size="small"
                sx={{
                  backgroundColor: tag.color || undefined,
                  color: tag.color ? "#fff" : undefined,
                }}
              />
            ))}
          </Box>
        )}
        {canEdit && (
          <Box sx={{ display: "flex", gap: 1 }}>
            <Button size="small" onClick={onEdit}>
              Edit
            </Button>
            <Button
              size="small"
              color="error"
              onClick={() => setConfirmDelete(true)}
            >
              Delete
            </Button>
          </Box>
        )}
        <Box sx={{ marginTop: 1 }}>
          <PostSourceForm topic={topic} />
        </Box>
        {!isLoading && items.length === 0 && <Empty>Nothing here yet.</Empty>}
        {items.map((item) => (
          <TopicFeedItem
            key={`${item.type}-${item.id}`}
            item={item}
            onRemove={
              item.type === "post" && (canEdit || item.author?.id === myId)
                ? () => removeTopicSource({ id: topic.id, objId: item.obj_id })
                : undefined
            }
          />
        ))}
        {hasNextPage && (
          <Button
            onClick={() => fetchNextPage()}
            disabled={isFetchingNextPage}
            sx={{ alignSelf: "center" }}
          >
            Load more
          </Button>
        )}
      </Body>
      <ConfirmDeletionDialog
        dialogOpen={confirmDelete}
        closeDialog={() => setConfirmDelete(false)}
        resourceName="topic"
        deleteFunction={async () => {
          const result = await deleteTopic(topic.id);
          setConfirmDelete(false);
          if (!result.error) onDeleted();
        }}
      />
    </Box>
  );
};

const Topics = () => {
  const [params, setParams] = useSearchParams();
  const narrow = useMediaQuery((theme: any) => theme.breakpoints.down("md"));
  const { data: profile } = useGetProfileQuery();
  const { data: topics } = useGetTopicsQuery();
  const [filter, setFilter] = useState<"all" | "subscribed">("all");
  const [search, setSearch] = useState("");
  const [editing, setEditing] = useState<Topic | "new" | null>(null);
  const topicId = params.get("id") ? Number(params.get("id")) : null;
  const topic = topics?.find((t) => t.id === topicId);
  const isAdmin = profile?.permissions?.includes("System admin");

  const shown = useMemo(() => {
    const query = search.trim().toLowerCase();
    return (topics ?? []).filter(
      (t) =>
        (filter === "all" || t.subscribed) &&
        (!query ||
          t.name.toLowerCase().includes(query) ||
          t.description?.toLowerCase().includes(query)),
    );
  }, [topics, filter, search]);

  const list = (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        minHeight: 0,
        height: "100%",
        width: narrow ? "100%" : "22rem",
        flexShrink: 0,
        borderRight: narrow ? 0 : 1,
        borderColor: "divider",
      }}
    >
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          padding: "0.75rem 0.75rem 0.5rem 1rem",
        }}
      >
        <Typography variant="h6" sx={{ flexGrow: 1, fontWeight: 600 }}>
          Topics
        </Typography>
        <Button
          size="small"
          variant="contained"
          onClick={() => setEditing("new")}
          data-testid="newTopicButton"
        >
          New topic
        </Button>
      </Box>
      <Box sx={{ padding: "0 0.75rem" }}>
        <TextField
          size="small"
          fullWidth
          placeholder="Search"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
      </Box>
      <Tabs
        value={filter}
        onChange={(_, value) => setFilter(value)}
        variant="fullWidth"
        sx={{ borderBottom: 1, borderColor: "divider", minHeight: 40 }}
      >
        <Tab value="all" label="All" sx={{ minHeight: 40 }} />
        <Tab value="subscribed" label="Subscribed" sx={{ minHeight: 40 }} />
      </Tabs>
      <List sx={{ flexGrow: 1, minHeight: 0, overflowY: "auto", padding: 0.5 }}>
        {topics && shown.length === 0 && (
          <Empty>{search ? "No match." : "No topic yet."}</Empty>
        )}
        {shown.map((t) => (
          <ListItemButton
            key={t.id}
            selected={t.id === topicId}
            onClick={() => setParams({ id: String(t.id) })}
            sx={{ borderRadius: 2, display: "block" }}
          >
            <Box sx={{ display: "flex", alignItems: "baseline", gap: 1 }}>
              <Typography
                noWrap
                sx={{ flexGrow: 1, fontWeight: t.subscribed ? 700 : 500 }}
              >
                {t.name}
              </Typography>
              <Typography
                variant="caption"
                color="textSecondary"
                sx={{ flexShrink: 0 }}
              >
                {t.subscriber_count}
              </Typography>
            </Box>
            {t.description && (
              <Typography variant="body2" color="textSecondary" noWrap>
                {t.description}
              </Typography>
            )}
          </ListItemButton>
        ))}
      </List>
    </Box>
  );

  const pane = topic ? (
    <TopicPane
      key={topic.id}
      topic={topic}
      myId={profile?.id}
      canEdit={Boolean(isAdmin || topic.creator?.id === profile?.id)}
      onEdit={() => setEditing(topic)}
      onDeleted={() => setParams({})}
      onBack={narrow ? () => setParams({}) : undefined}
    />
  ) : (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        height: "100%",
        gap: 2,
        padding: 2,
      }}
    >
      <Typography color="textSecondary">
        {topicId && topics ? "This topic does not exist." : "Pick a topic."}
      </Typography>
    </Box>
  );

  return (
    <Box
      sx={{
        display: "flex",
        height: "calc(100vh - 4rem)",
        margin: "-0.625rem",
        overflow: "hidden",
        backgroundColor: "background.paper",
      }}
    >
      {(!narrow || !topic) && list}
      {(!narrow || topic) && (
        <Box sx={{ flexGrow: 1, minWidth: 0, minHeight: 0 }}>{pane}</Box>
      )}
      {editing && (
        <TopicDialog
          topic={editing === "new" ? undefined : editing}
          onClose={() => setEditing(null)}
          onSaved={(id) => {
            setEditing(null);
            setParams({ id: String(id) });
          }}
        />
      )}
    </Box>
  );
};

export default Topics;
