import React, { useEffect } from "react";
import PropTypes from "prop-types";
import { useSelector, useDispatch } from "react-redux";

import { useTheme } from "@mui/material/styles";
import { useMediaQuery } from "@mui/material";
import withRouter from "./withRouter";

import SourceDesktop from "./SourceDesktop";
import SourceMobile from "./SourceMobile";
import Spinner from "./Spinner";

import * as Action from "../ducks/source";

const Source = ({ route }) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("lg"));
  const dispatch = useDispatch();
  const source = useSelector((state) => state.source);
  const cachedSourceId = source ? source.id : null;
  const isCached = route.id === cachedSourceId;

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
    <div>
      {isMobile ? (
        <SourceMobile source={source} />
      ) : (
        <SourceDesktop source={source} />
      )}
    </div>
  );
};

Source.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string,
  }).isRequired,
};

export default withRouter(Source);
