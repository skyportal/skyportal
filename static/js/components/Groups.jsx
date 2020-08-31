import React from "react";
import { useSelector } from "react-redux";

import GroupManagement from "./GroupManagement";
import GroupList from "./GroupList";

const Groups = () => {
  const roles = useSelector((state) => state.profile.roles);
  const groups = useSelector((state) => state.groups.user);

  return (
    <div>
      <GroupList title="My Groups" groups={groups} />
      <br />
      {roles.includes("Super admin") && <GroupManagement />}
    </div>
  );
};

export default Groups;
