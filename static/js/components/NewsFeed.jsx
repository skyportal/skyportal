import React from 'react';
import { Link } from 'react-router-dom';
import { useSelector } from 'react-redux';


const NewsFeed = () => {
  const { comments, sources, photometry } = useSelector((state) => state.newsFeed);
  return (
    <div>
      <h2>
        News Feed
      </h2>
      <div>
        <h4>
          Newest Comments:
        </h4>
        <ul>
          {
            comments.map((comment) => (
              <li>
                Source:&nbsp;
                <Link to={`/source/${comment.source_id}`}>
                  {comment.source_id}
                </Link>
                ;&nbsp;type: {comment.ctype}; author: {comment.author};
                <br />
                text: {comment.text}
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
            sources.map((source) => (
              <li>
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
            photometry.map((phot) => (
              <li>
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
