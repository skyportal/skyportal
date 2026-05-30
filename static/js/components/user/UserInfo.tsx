import React, { useEffect } from "react";
import CircularProgress from "@mui/material/CircularProgress";

import { useAppDispatch, useAppSelector } from "../../types/hooks";
import withRouter from "../withRouter";

import * as Action from "../../ducks/users";

interface UserInfoProps {
  route: {
    id: string;
  };
}

const UserInfo = ({ route }: UserInfoProps) => {
  const dispatch = useAppDispatch();
  const user = useAppSelector((state) => state.users.user);
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

export default withRouter(UserInfo);
