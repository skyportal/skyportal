import { useEffect } from "react";
import { Link, useParams } from "react-router-dom";

import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
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

  if (filterError)
    return (filterError as any)?.error ?? "Failed to load filter";
  if (filter == null) return <Spinner />;

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <IconButton
          component={Link}
          to={`/group/${group_id}?tab=filters`}
          aria-label="back to group filters"
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
      </Box>
      {brokerId && <AssistantHint />}
      {group && <FilterPlugins />}
    </Box>
  );
};

export default Filter;
