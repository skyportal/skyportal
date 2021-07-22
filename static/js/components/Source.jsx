import React, { useEffect, useState, useRef } from "react";
import PropTypes from "prop-types";
import { useSelector, useDispatch } from "react-redux";

import { useTheme } from "@material-ui/core/styles";
import Paper from "@material-ui/core/Paper";
import CircularProgress from "@material-ui/core/CircularProgress";

import * as Action from "../ducks/source";
import SourceDesktop from "./SourceDesktop";
import SourceMobile from "./SourceMobile";

const sidebarWidth = 190;

const Source = ({ route }) => {
  const ref = useRef(null);
  const theme = useTheme();
  const initialWidth = window.innerWidth - sidebarWidth - 2 * theme.spacing(2);
  const [width, setWidth] = useState(initialWidth);
  const dispatch = useDispatch();
  const source = useSelector((state) => state.source);
  const cachedSourceId = source ? source.id : null;
  const isCached = route.id === cachedSourceId;

  useEffect(() => {
    const handleResize = () => {
      if (ref.current !== null) {
        setWidth(ref.current.offsetWidth);
      }
    };

    window.addEventListener("resize", handleResize);
  }, [ref]);

  useEffect(() => {
    const fetchSource = async () => {
      const data = await dispatch(Action.fetchSource(route.id));
      if (data.status === "success") {
        dispatch(Action.addSourceView(route.id));
      }
    };

    if (!isCached) {
      fetchSource();
    }
  }, [dispatch, isCached, route.id]);

  if (source.loadError) {
    return <div>{source.loadError}</div>;
  }
  if (!isCached) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }
  if (source.id === undefined) {
    return <div>Source not found</div>;
  }
  document.title = source.id;

  return (
    <Paper ref={ref} elevation={1}>
      {width <= 1200 ? (
        <SourceMobile source={source} />
      ) : (
        <SourceDesktop source={source} />
      )}
    </Paper>
  );
};

Source.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string,
  }).isRequired,
};

export default Source;
