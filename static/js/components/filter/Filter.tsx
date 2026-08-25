import { useEffect } from "react";
import { Link, useParams } from "react-router-dom";

import Grid from "@mui/material/Grid";
import Typography from "@mui/material/Typography";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";

import { showNotification } from "baselayer/components/Notifications";

import { useAppDispatch } from "../../types/hooks";
import FilterPlugins from "./FilterPlugins";
import Spinner from "../Spinner";

import { useGetGroupQuery } from "../../ducks/group";
import { useGetFilterQuery } from "../../ducks/filter";
import { useGetStreamQuery } from "../../ducks/stream";

const Filter = () => {
  const dispatch = useAppDispatch();

  const { fid } = useParams();

  const { data: filter, error: filterError } = useGetFilterQuery(fid ?? "", {
    skip: !fid,
  }) as any;
  const filterLoadError = filterError
    ? ((filterError as any)?.error ?? "Failed to load filter")
    : "";

  const group_id = filter?.group_id;
  const stream_id = filter?.stream_id;

  const { data: group, error: groupError } = useGetGroupQuery(group_id, {
    skip: !group_id,
  }) as any;

  useEffect(() => {
    if (groupError) {
      const message = (groupError as any)?.error ?? "Failed to load group";
      if (message.length > 1) {
        dispatch(showNotification(message, "error"));
      }
    }
  }, [groupError, dispatch]);

  const { data: stream } = useGetStreamQuery(stream_id ?? "", {
    skip: !stream_id,
  });

  if (filterLoadError) return filterLoadError;

  if (filter == null) return <Spinner />;

  return (
    <div>
      <Typography variant="h6" sx={{ mb: 1 }}>
        <b>Filter:</b> {filter.name}
      </Typography>

      <Grid container spacing={2}>
        {group && stream && (
          <Grid size={{ sm: 12, md: 12 }}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Group: <Link to={`/group/${group.id}`}>{group.name}</Link>
                  <br />
                  Group id: {group.id}
                  <br />
                  Stream: {stream["name"]}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        )}
        <Grid size={{ sm: 12, md: 12 }}>
          {group && <FilterPlugins group={group} />}
        </Grid>
      </Grid>
    </div>
  );
};

export default Filter;
