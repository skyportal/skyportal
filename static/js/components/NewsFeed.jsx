import React from 'react';
import { Link } from 'react-router-dom';
import { useSelector } from 'react-redux';

import WidgetPrefsDialog from './WidgetPrefsDialog';
import * as ProfileActions from '../ducks/profile';


const NewsFeed = () => {
  const { comments, sources, photometry } = useSelector((state) => state.newsFeed);
  const profile = useSelector((state) => state.profile);

  const newsFeedPrefs = (
    profile != null && profile.hasOwnProperty("preferences") &&
    profile.preferences != null && profile.preferences.hasOwnProperty("newsFeed")) ?
                        profile.preferences.newsFeed : { numItemsPerCategory: "" };
  return (
    <div style={{ border: "1px solid #DDD", padding: "10px" }}>
      <h2 style={{ display: "inline-block" }}>
        News Feed
      </h2>
      <div style={{ display: "inline-block", float: "right" }}>
        <WidgetPrefsDialog
          formValues={newsFeedPrefs}
          stateBranchName="newsFeed"
          title="News Feed Preferences"
          onSubmit={ProfileActions.updateUserPreferences}
        />
      </div>
      <div>
        <h4>
          Newest Comments:
        </h4>
        <ul>
          {
            comments.map((comment, idx) => (
              <li key={`comment${idx}`}>
                Source:&nbsp;
                <Link to={`/source/${comment.source_id}`}>
                  {comment.source_id}
                </Link>
                ;&nbsp;type: {comment.ctype}; author: {comment.author};
                <br />
                text: <i>{comment.text}</i>
              </li>
            ))
          }
        </ul>
      </div>
      <div>
        <h4>
          Newest Sources:
        </h4>
        <ul>
          {
            sources.map((source, idx) => (
              <li key={`source${idx}`}>
                <Link to={`/source/${source.id}`}>
                  {source.id}
                </Link>
              </li>
            ))
          }
        </ul>
      </div>
      <div>
        <h4>
          Newest Photometry:
        </h4>
        <ul>
          {
            photometry.map((phot, idx) => (
              <li key={`phot${idx}`}>
                {phot.id} (source:&nbsp;
                <Link to={`/source/${phot.source_id}`}>
                  {phot.source_id}
                </Link>
                )
              </li>
            ))
          }
        </ul>
      </div>
    </div>
  );
};

export default NewsFeed;
