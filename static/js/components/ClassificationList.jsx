import React, { useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import { Button } from "@material-ui/core";
import Tooltip from "@material-ui/core/Tooltip";
import GroupIcon from "@material-ui/icons/Group";
import ListItem from "@material-ui/core/ListItem";
import { FixedSizeList } from "react-window";

import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import utc from "dayjs/plugin/utc";

import * as sourceActions from "../ducks/source";
import styles from "./ClassificationList.css";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const ClassificationList = () => {
  const [hoverID, setHoverID] = useState(null);

  const handleMouseHover = (id, userProfile, author) => {
    if (
      userProfile.permissions.includes("System admin") ||
      userProfile.permissions.includes("Manage groups") ||
      userProfile.username === author
    ) {
      setHoverID(id);
    }
  };

  const handleMouseLeave = () => {
    setHoverID(null);
  };

  const dispatch = useDispatch();
  const { taxonomyList } = useSelector((state) => state.taxonomies);
  const source = useSelector((state) => state.source);
  const obj = source;
  const userProfile = useSelector((state) => state.profile);
  // const acls = useSelector((state) => state.profile.acls);
  let { classifications } = obj;

  classifications = classifications || [];

  // newest classifications on top reverse sort the classifications by created_at
  const sorted_classifications = classifications.sort((a, b) =>
    a.created_at > b.created_at ? -1 : 1
  );

  const items = sorted_classifications.map(
    ({
      id,
      author_name,
      created_at,
      classification,
      probability,
      taxonomy_id,
      groups,
    }) => {
      let taxname = taxonomyList.filter((i) => i.id === taxonomy_id);
      if (taxname.length > 0) {
        taxname = taxname[0].name;
      } else {
        taxname = "Unknown taxonomy";
      }
      return (
        <ListItem
          key={id}
          className={styles.classification}
          style={{ alignItems: "start" }}
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
              {dayjs().to(dayjs.utc(`${created_at}Z`))}
            </span>
            &nbsp;
            <Tooltip title={groups.map((group) => group.name).join(", ")}>
              <GroupIcon
                fontSize="small"
                style={{ paddingTop: "6px", paddingBottom: "0px" }}
              />
            </Tooltip>
          </div>
          <div className={styles.wrap} data-testid={`classificationDiv_${id}`}>
            <div className={styles.classificationMessage}>
              <span style={{ fontWeight: "bold", fontSize: "120%" }}>
                {classification}
              </span>{" "}
              <span>{`(P=${probability})`}</span>
              <div>
                <i>{taxname}</i>
              </div>
            </div>
            <div
              style={{
                width: "60px",
                marginLeft: "0",
                marginRight: "auto",
                background: "none",
                height: "70px",
                display: "inline-block",
              }}
            />
            <Button
              style={
                hoverID === id
                  ? { visibility: "visible", display: "block", margin: "1%" }
                  : { visibility: "hidden", display: "block", margin: "1%" }
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
        </ListItem>
      );
    }
  );

  const Row = ({ index }) => items[index];

  return (
    <div
      style={{ display: classifications.length > 0 ? "block" : "none" }}
      className={styles.classifications}
    >
      <FixedSizeList
        className={styles.classifications}
        height={Math.min(360, parseInt(classifications.length * 120, 10))}
        width={350}
        itemSize={80}
        itemCount={items.length}
      >
        {Row}
      </FixedSizeList>
    </div>
  );
};

ClassificationList.propTypes = {};

export default ClassificationList;
