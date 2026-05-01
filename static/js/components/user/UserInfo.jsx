import React, { useEffect } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";

import CircularProgress from "@mui/material/CircularProgress";
import withRouter from "../withRouter";

import * as Action from "../../ducks/users";

const UserInfo = ({ route }) => {
  const dispatch = useDispatch();
  const user = useSelector((state) => state.users.user);
  useEffect(() => {
    dispatch(Action.fetchUser(route.id));
  }, [route.id, dispatch]);
  if (user?.id !== Number(route.id)) {
    return <CircularProgress color="secondary" />;
  }
  const { username, created_at, permissions } = user;
  return (
    <div>
      <b>{username}</b>
      <ul>
        <li>
          <b>Created at:</b> {created_at}
        </li>
        <li>
          <b>All ACLs:</b> {permissions.join(", ")}
        </li>
      </ul>
    </div>
  );
};
UserInfo.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string,
  }).isRequired,
};

export default withRouter(UserInfo);
