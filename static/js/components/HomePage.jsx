import React from "react";
import { useSelector } from "react-redux";

import RecentSources from "./RecentSources";
import GroupList from "./GroupList";
import NewsFeed from "./NewsFeed";
import TopSources from "./TopSources";
import UninitializedDBMessage from "./UninitializedDBMessage";
import styles from "./HomePage.css";

const HomePage = () => {
  const groups = useSelector((state) => state.groups.user);

  const sourceTableEmpty = useSelector(
    (state) => state.dbInfo.source_table_empty
  );
  if (sourceTableEmpty) {
    return <UninitializedDBMessage />;
  }

  return (
    <div>
      <div className={styles.homePageWidgetDiv}>
        <RecentSources />
      </div>
      <div className={styles.homePageWidgetDiv}>
        <NewsFeed />
      </div>
      <div className={styles.homePageWidgetDiv}>
        <TopSources />
      </div>
      <div className={styles.homePageWidgetDiv}>
        <GroupList title="My Groups" groups={groups} />
      </div>
    </div>
  );
};

export default HomePage;
