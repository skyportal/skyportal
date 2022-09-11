import React, { useEffect, useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import PropTypes from "prop-types";

import * as tnsInfoActions from "../ducks/tnsInfo";

const TNSInfo = ({ objID }) => {
  const dispatch = useDispatch();
  const [requestsSubmitted, setRequestsSubmitted] = useState([]);
  const tnsInfo = useSelector((state) => state.tnsInfo);

  useEffect(
    // eslint-disable-next-line
    function fetchTNSInfo() {
      if (
        !requestsSubmitted.includes(objID) &&
        (tnsInfo === null || !Object.keys(tnsInfo).includes(objID))
      ) {
        dispatch(tnsInfoActions.fetchTNSInfo(objID));
        setRequestsSubmitted([...requestsSubmitted, objID]);
      }
    },
    [objID, dispatch, tnsInfo, requestsSubmitted]
  );

  if (tnsInfo === null || !Object.keys(tnsInfo).includes(objID)) {
    return <>Fetching TNS data...</>;
  }
  const objTnsInfo = tnsInfo[objID];

  return (
    <span>
      {objTnsInfo !== null && objTnsInfo?.length > 0
        ? objTnsInfo.map((TNSMatch) => {
            if (
              typeof TNSMatch.name === "string" &&
              TNSMatch.name.split(" ").length === 2
            ) {
              return (
                <a
                  key={TNSMatch.name}
                  href={`https://www.wis-tns.org/object/${
                    TNSMatch.name.split(" ")[1]
                  }`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {`${TNSMatch.name} `}
                </a>
              );
            }
            return TNSMatch.name;
          })
        : `No matches found`}
    </span>
  );
};
TNSInfo.propTypes = {
  objID: PropTypes.string.isRequired,
};

export default TNSInfo;
