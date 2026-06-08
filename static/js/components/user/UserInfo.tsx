import CircularProgress from "@mui/material/CircularProgress";

import withRouter from "../withRouter";

import { useGetUserQuery } from "../../ducks/users";

interface UserInfoProps {
  route: {
    id: string;
  };
}

const UserInfo = ({ route }: UserInfoProps) => {
  const { data: user } = useGetUserQuery(route.id);
  if (user?.id !== Number(route.id)) {
    return <CircularProgress color="secondary" />;
  }
  const { username } = user;
  const created_at = user["created_at"] as string | undefined;
  const permissions = (user["permissions"] as string[] | undefined) ?? [];
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
