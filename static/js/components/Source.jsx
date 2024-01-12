import React, { useEffect, useState, useRef } from "react";
import PropTypes from "prop-types";
import { useSelector, useDispatch } from "react-redux";

import { useTheme } from "@mui/material/styles";
import Paper from "@mui/material/Paper";

import * as Action from "../ducks/source";
import SourceDesktop from "./SourceDesktop";
import SourceMobile from "./SourceMobile";
import Spinner from "./Spinner";

import withRouter from "./withRouter";

const sidebarWidth = 170;

const Source = ({ route }) => {
  const ref = useRef(null);
  const theme = useTheme();
  const initialWidth =
    window.innerWidth - sidebarWidth - 2 * parseInt(theme.spacing(2), 10);
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
        <Spinner />
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

export default withRouter(Source);
