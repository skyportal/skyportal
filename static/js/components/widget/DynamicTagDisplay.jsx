import React, { useEffect, useState, useRef, useMemo } from "react";
import { useSelector, useDispatch } from "react-redux";
import { Chip, Tooltip } from "@mui/material";
import PropTypes from "prop-types";
import { getContrastColor } from "../ObjectTags";
import * as groupsActions from "../../ducks/groups";

const DynamicTagDisplay = ({ source, styles, displayTags = true }) => {
  const [visibleTagsCount, setVisibleTagsCount] = useState(2);
  const [containerWidth, setContainerWidth] = useState(0);
  const containerRef = useRef(null);
  const measureRef = useRef(null);
  const dispatch = useDispatch();

  const tagOptions = useSelector((state) => state.objectTags || []);
  const userGroups = useSelector((state) => state.groups.userAccessible);

  useEffect(() => {
    if (!userGroups || userGroups.length === 0) {
      dispatch(groupsActions.fetchGroups());
    }
  }, [dispatch, userGroups]);

  // Filter tags to only show those the user has access to (via group membership)
  const userGroupIds = useMemo(
    () => new Set(userGroups?.map((g) => g.id) || []),
    [userGroups],
  );

  const accessibleTags = useMemo(() => {
    if (!source.tags) return [];
    return source.tags.filter((tag) => {
      if (!tag.groups || tag.groups.length === 0) return false;
      return tag.groups.some((group) => userGroupIds.has(group.id));
    });
  }, [source.tags, userGroupIds]);

  const measureTextWidth = (text) => {
    if (!measureRef.current) return 0;

    // Temporary element to calculate the space it takes
    const tempElement = document.createElement("span");
    tempElement.style.visibility = "hidden";
    tempElement.style.position = "absolute";
    tempElement.style.whiteSpace = "nowrap";
    tempElement.style.fontSize = "0.8125rem";
    tempElement.style.fontFamily = window.getComputedStyle(
      measureRef.current,
    ).fontFamily;
    tempElement.style.padding = "4px 12px";
    tempElement.textContent = text;

    document.body.appendChild(tempElement);
    const width = tempElement.offsetWidth + 8;
    document.body.removeChild(tempElement);

    return width;
  };

  // Calculate how many tags we can put on the container
  const calculateVisibleTags = () => {
    if (!accessibleTags || accessibleTags.length === 0 || !containerRef.current) {
      return accessibleTags?.length || 0;
    }

    const availableWidth = containerRef.current.offsetWidth;
    let totalWidth = 0;
    let visibleCount = 0;

    for (let i = 0; i < accessibleTags.length; i++) {
      const tagWidth = measureTextWidth(accessibleTags[i].name);

      const remainingTags = accessibleTags.length - i;
      const needsPlusChip = remainingTags > 1;
      const plusChipWidth = needsPlusChip
        ? measureTextWidth(`+${remainingTags - 1}`)
        : 0;

      if (totalWidth + tagWidth + plusChipWidth <= availableWidth) {
        totalWidth += tagWidth;
        visibleCount++;
      } else {
        break;
      }
    }

    return Math.max(1, Math.min(visibleCount, accessibleTags.length));
  };

  useEffect(() => {
    if (!containerRef.current) return;

    const resizeObserver = new ResizeObserver((entries) => {
      for (let entry of entries) {
        const newWidth = entry.contentRect.width;
        if (newWidth !== containerWidth) {
          setContainerWidth(newWidth);
        }
      }
    });

    resizeObserver.observe(containerRef.current);

    return () => {
      resizeObserver.disconnect();
    };
  }, [containerWidth]);

  useEffect(() => {
    if (containerWidth > 0 && accessibleTags) {
      const newVisibleCount = calculateVisibleTags();
      setVisibleTagsCount(newVisibleCount);
    }
  }, [containerWidth, accessibleTags]);

  useEffect(() => {
    if (containerRef.current && containerWidth === 0) {
      setContainerWidth(containerRef.current.offsetWidth);
    }
  }, []);

  if (!displayTags || !accessibleTags || accessibleTags.length === 0) {
    return null;
  }

  const hasMoreTags = accessibleTags.length > visibleTagsCount;
  const visibleTags = accessibleTags.slice(0, visibleTagsCount);
  const hiddenTags = accessibleTags.slice(visibleTagsCount);

  const visibleTagsWithColors = visibleTags.map((tag) => {
    const tagOption = tagOptions.find(
      (option) => option.id === tag.objtagoption_id,
    );
    return {
      ...tag,
      color: tagOption?.color || "#dddfe2",
    };
  });

  const hiddenTagsWithColors = hiddenTags.map((tag) => {
    const tagOption = tagOptions.find(
      (option) => option.id === tag.objtagoption_id,
    );
    return {
      ...tag,
      color: tagOption?.color || "#dddfe2",
    };
  });

  return (
    <div className={styles.tagsContainer} ref={containerRef}>
      <span
        ref={measureRef}
        style={{ visibility: "hidden", position: "absolute" }}
      />

      {visibleTagsWithColors.map((tag) => (
        <Chip
          key={tag.id}
          label={tag.name}
          size="small"
          className={styles.tagChip}
          variant="filled"
          style={{
            backgroundColor: tag.color,
            color: getContrastColor(tag.color),
          }}
        />
      ))}

      {hasMoreTags && (
        <Tooltip
          title={
            <div>
              <strong>Additional tags:</strong>
              <br />
              {hiddenTagsWithColors.map((tag, index) => (
                <span key={tag.id}>
                  <Chip
                    label={tag.name}
                    size="small"
                    style={{
                      backgroundColor: tag.color,
                      color: getContrastColor(tag.color),
                      margin: "2px",
                    }}
                  />
                  {index < hiddenTagsWithColors.length - 1 ? " " : ""}
                </span>
              ))}
            </div>
          }
        >
          <Chip
            key="more-tags"
            label={`+${hiddenTags.length}`}
            size="small"
            className={styles.tagChip}
            color="default"
            variant="filled"
            style={{
              fontStyle: "italic",
              opacity: 0.7,
            }}
          />
        </Tooltip>
      )}
    </div>
  );
};

DynamicTagDisplay.propTypes = {
  source: PropTypes.shape({
    tags: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number.isRequired,
        name: PropTypes.string.isRequired,
        groups: PropTypes.arrayOf(
          PropTypes.shape({
            id: PropTypes.number.isRequired,
          }),
        ),
      }),
    ),
  }).isRequired,
  styles: PropTypes.shape({
    tagsContainer: PropTypes.string.isRequired,
    tagChip: PropTypes.string.isRequired,
  }).isRequired,
  displayTags: PropTypes.bool.isRequired,
};

export default DynamicTagDisplay;
