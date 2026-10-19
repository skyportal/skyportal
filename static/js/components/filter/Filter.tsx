import { useEffect } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";

import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";

import { showNotification } from "baselayer/components/Notifications";

import { useAppDispatch } from "../../types/hooks";
import FilterPlugins from "./FilterPlugins";
import Spinner from "../Spinner";

import {
  useCommentPanel,
  useCommentTarget,
} from "../../contexts/CommentPanelContext";
import { useGetConfigQuery } from "../../ducks/config";
import { useGetGroupQuery } from "../../ducks/group";
import { useGetFilterQuery } from "../../ducks/filter";
import { useGetStreamQuery } from "../../ducks/stream";
import { useGetBrokerCredentialsQuery } from "../../ducks/brokers";

const AssistantHint = () => {
  const { setSpace, setOpen } = useCommentPanel();
  if (useGetConfigQuery().data?.["assistantEnabled"] !== true) return null;

  return (
    <Alert
      severity="info"
      icon={<SmartToyIcon color="primary" />}
      action={
        <Button
          color="inherit"
          size="small"
          onClick={() => {
            setSpace("assistant");
            setOpen(true);
          }}
        >
          Open assistant
        </Button>
      }
      sx={{ border: 1, borderColor: "divider" }}
    >
      The assistant knows which filter you are on and can read it. Ask it to
      explain, fix or extend this filter. We recommend using it when writing or
      changing a filter.
    </Alert>
  );
};

const Filter = () => {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const location = useLocation();
  const { fid } = useParams();

  const { data: filter, error: filterError } = useGetFilterQuery(fid ?? "", {
    skip: !fid,
  }) as any;
  const group_id = filter?.group_id;
  const brokerId = filter?.broker_id;

  useCommentTarget(
    brokerId ? { type: "filter", id: filter.id, brokerId } : null,
  );

  const { data: group, error: groupError } = useGetGroupQuery(group_id, {
    skip: !group_id,
  }) as any;

  useEffect(() => {
    if (!groupError) return;
    const message = (groupError as any)?.error ?? "Failed to load group";
    if (message.length > 1) dispatch(showNotification(message, "error"));
  }, [groupError, dispatch]);

  const { data: stream } = useGetStreamQuery(filter?.stream_id ?? "", {
    skip: !filter?.stream_id,
  });

  const { data: credentials } = useGetBrokerCredentialsQuery(brokerId, {
    skip: !brokerId,
  });
  // A topic with no status yet has had nothing consumed from it, which is not
  // the same as one ingestion has found it cannot read.
  const myTopics = Object.entries(credentials?.topic_filter_ids ?? {})
    .filter(([, ids]) => ids.includes(filter?.id))
    .map(([topic]) => ({ topic, status: credentials?.topic_status?.[topic] }));
  const faulted = myTopics.filter(({ status }) => status?.usable === false);

  if (filterError)
    return (filterError as any)?.error ?? "Failed to load filter";
  if (filter == null) return <Spinner />;

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <IconButton
          aria-label="back"
          onClick={() =>
            location.key === "default"
              ? navigate(`/group/${group_id}?tab=filters`)
              : navigate(-1)
          }
        >
          <ArrowBackIcon />
        </IconButton>
        <Typography variant="h6">
          <b>Filter:</b> {filter.name}
        </Typography>
        {group && (
          <Chip
            size="small"
            label={`Group: ${group.name}`}
            component={Link}
            to={`/group/${group.id}`}
            clickable
          />
        )}
        {stream && <Chip size="small" label={`Stream: ${stream["name"]}`} />}
        {myTopics.map(({ topic, status }) => (
          <Tooltip
            key={topic}
            title={
              status === undefined
                ? "Nothing consumed from this topic yet"
                : (status.detail ?? `Delivering as of ${status.at}`)
            }
          >
            <Chip
              size="small"
              label={topic}
              variant="outlined"
              color={status?.usable === false ? "error" : "primary"}
            />
          </Tooltip>
        ))}
      </Box>
      {faulted.map(({ topic, status }) => (
        <Alert key={topic} severity="warning">
          <b>{topic}</b>: {status?.detail}
        </Alert>
      ))}
      {brokerId && <AssistantHint />}
      {group && <FilterPlugins />}
    </Box>
  );
};

export default Filter;
