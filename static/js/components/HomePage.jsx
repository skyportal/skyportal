import React from "react";
import { useSelector } from "react-redux";

import SourceList from "./SourceList";
import GroupList from "./GroupList";
import NewsFeed from "./NewsFeed";
import TopSources from "./TopSources";
import styles from "./HomePage.css";

const HomePage = () => {
  const groups = useSelector((state) => state.groups.user);
  return (
    <div>
      <div className={styles.homePageWidgetDiv}>
        <SourceList />
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
