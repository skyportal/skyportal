import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link, useParams } from "react-router-dom";

import Grid from "@mui/material/Grid";
import Typography from "@mui/material/Typography";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";

import { showNotification } from "baselayer/components/Notifications";

import FilterPlugins from "./FilterPlugins";
import Spinner from "../Spinner";
import * as groupActions from "../../ducks/group";
import * as filterActions from "../../ducks/filter";
import * as streamActions from "../../ducks/stream";

const Filter = () => {
  const dispatch = useDispatch();
  const [filterLoadError, setFilterLoadError] = useState("");
  const [groupLoadError, setGroupLoadError] = useState("");
  const [streamLoadError, setStreamLoadError] = useState("");

  const { fid } = useParams();
  const loadedId = useSelector((state) => state.filter.id);

  useEffect(() => {
    const fetchFilter = async () => {
      const data = await dispatch(filterActions.fetchFilter(fid));
      if (data.status === "error") {
        setFilterLoadError(data.message);
      }
    };
    if (loadedId !== fid) {
      fetchFilter();
    }
  }, [fid, loadedId, dispatch]);

  const group_id = useSelector((state) => state.filter.group_id);
  const stream_id = useSelector((state) => state.filter.stream_id);

  useEffect(() => {
    const fetchGroup = async () => {
      const data = await dispatch(groupActions.fetchGroup(group_id));
      if (data.status === "error") {
        setGroupLoadError(data.message);
        if (groupLoadError.length > 1) {
          dispatch(showNotification(groupLoadError, "error"));
        }
      }
    };
    if (group_id) fetchGroup();
  }, [group_id, dispatch, groupLoadError]);

  useEffect(() => {
    const fetchStream = async () => {
      const data = await dispatch(streamActions.fetchStream(stream_id));
      if (data.status === "error") {
        setStreamLoadError(data.message);
        if (streamLoadError.length > 1) {
          dispatch(showNotification(streamLoadError, "error"));
        }
      }
    };
    if (stream_id) fetchStream();
  }, [stream_id, dispatch, streamLoadError]);

  const filter = useSelector((state) => state.filter);
  const group = useSelector((state) => state.group);
  const stream = useSelector((state) => state.stream);

  if (filterLoadError) return filterLoadError;

  if (!filter) return <Spinner />;

  return (
    <div>
      <Typography variant="h6" mb={1}>
        <b>Filter:</b> {filter.name}
      </Typography>
      <Grid container spacing={2}>
        {group && stream && (
          <Grid item sm={12} md={12}>
            <Card>
              <CardContent>
                <Typography color="textSecondary">
                  Group: <Link to={`/group/${group.id}`}>{group.name}</Link>
                  <br />
                  Group id: {group.id}
                  <br />
                  Stream: {stream.name}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        )}
        <Grid item sm={12} md={12}>
          <FilterPlugins group={group} />
        </Grid>
      </Grid>
    </div>
  );
};

export default Filter;
