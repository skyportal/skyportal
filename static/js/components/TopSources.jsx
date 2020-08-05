import React from 'react';
import { useSelector } from 'react-redux';
import { Link } from 'react-router-dom';

import * as profileActions from '../ducks/profile';
import WidgetPrefsDialog from './WidgetPrefsDialog';

const defaultPrefs = {
  maxNumSources: "",
  sinceDaysAgo: ""
};

const TopSources = () => {
  const { sourceViews } = useSelector((state) => state.topSources);
  const topSourcesPrefs = useSelector(
    (state) => state.profile.preferences.topSources
  ) || defaultPrefs;

  return (
    <div style={{ border: "1px solid #DDD", padding: "10px" }}>
      <h2 style={{ display: "inline-block" }}>
        Top Sources
      </h2>
      <div style={{ display: "inline-block", float: "right" }}>
        <WidgetPrefsDialog
          formValues={topSourcesPrefs}
          stateBranchName="topSources"
          title="Top Sources Preferences"
          onSubmit={profileActions.updateUserPreferences}
        />
      </div>
      <p>
        Displaying most-viewed sources
      </p>
      <ul style={{ listStyleType: "none" }}>
        {
          sourceViews.map(({ obj_id, views, public_url }) => (
            <li key={`topSources_${obj_id}_${views}`}>
              <span>
                <img src={public_url} alt={obj_id} width="50%" height="50%" />
              </span>
              <span>
                <Link to={`/source/${obj_id}`}>
                  {obj_id}
                </Link>
              </span>
              <span>
                <em>
                  &nbsp;
                  -&nbsp;
                  {views}
                  &nbsp;view(s)
                </em>
              </span>
            </li>
          ))
        }
      </ul>
    </div>
  );
};

export default TopSources;
