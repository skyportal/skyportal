import React, { useState } from "react";
import PropTypes from "prop-types";
import { useSelector, useDispatch } from "react-redux";
import { Button } from "@material-ui/core";
import Tooltip from "@material-ui/core/Tooltip";
import GroupIcon from "@material-ui/icons/Group";

import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";

import * as sourceActions from "../ducks/source";
import styles from "./ClassificationList.css";

dayjs.extend(relativeTime);

const ClassificationList = ({ isCandidate }) => {
  const [hoverID, setHoverID] = useState(null);

  const handleMouseHover = (id, userProfile, author) => {
    if (userProfile.roles.includes("Super admin") || userProfile.username === author) {
      setHoverID(id);
    }
  };

  const handleMouseLeave = () => {
    setHoverID(null);
  };

  const dispatch = useDispatch();
  const source = useSelector((state) => state.source);
  const candidate = useSelector((state) => state.candidate);
  const obj = isCandidate ? candidate : source;
  const userProfile = useSelector((state) => state.profile);
  const acls = useSelector((state) => state.profile.acls);
  let { classifications } = obj;

  classifications = classifications || [];

  const items = classifications.map(
    ({ id, author_name, created_at, classification, probability, taxonomy_id, groups }) => (
      <span
        key={id}
        className={styles.classification}
        onMouseOver={() => handleMouseHover(id, userProfile, author_name)}
        onMouseOut={() => handleMouseLeave()}
        onFocus={() => handleMouseHover(id, userProfile, author_name)}
        onBlur={() => handleMouseLeave()}
      >
        <div className={styles.classificationHeader}>
          <span className={styles.classificationUser}>
            <span className={styles.classificationUserName}>
              {author_name}
            </span>
          </span>
          &nbsp;
          <span className={styles.classificationTime}>
            {dayjs().to(dayjs(created_at))}
          </span>
          &nbsp;
          <Tooltip title={groups.map((group) => group.name).join(", ")}>
            <GroupIcon fontSize="small" style={{ paddingTop: "6px", paddingBottom: "0px" }} />
          </Tooltip>
        </div>
        <div className={styles.wrap} name={`classificationDiv${id}`}>
          <div className={styles.classificationMessage}>
            {classification} (P={probability})
          </div>
          <Button
            style={
              hoverID === id ? { display: "block" } : { display: "none" }
            }
            size="small"
            variant="outlined"
            color="primary"
            type="button"
            name={`deleteClassificationButton${id}`}
            onClick={() => {
              dispatch(sourceActions.deleteClassification(id));
            }}
            className={styles.classificationDelete}
          >
            🗑
          </Button>
        </div>

      </span>
    )
  );
  return (
    <div className={styles.classifications}>
      {items}
    </div>
  );
};

ClassificationList.propTypes = {
};

ClassificationList.defaultProps = {
  isClassification: false
};

export default ClassificationList;
