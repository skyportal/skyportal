import { useCallback, useEffect, useState, useRef, useMemo } from "react";
import { Chip, Tooltip } from "@mui/material";
import { getContrastColor } from "../ObjectTags";
import { useGetGroupsQuery } from "../../ducks/groups";
import * as objectTagsActions from "../../ducks/objectTags";
import { useAppSelector, useAppDispatch } from "../../types/hooks";

interface DynamicTagDisplayProps {
  source: {
    tags?: {
      id: number;
      name: string;
      objtagoption_id?: number;
      groups?: { id: number }[];
    }[];
  };
  styles: Record<string, string>;
}

const DynamicTagDisplay = ({ source, styles }: DynamicTagDisplayProps) => {
  const [visibleTagsCount, setVisibleTagsCount] = useState(2);
  const [containerWidth, setContainerWidth] = useState(0);
  const containerRef = useRef<any>(null);
  const measureRef = useRef<any>(null);
  const dispatch = useAppDispatch();
  const tagOptions = useAppSelector((state: any) => state.objectTags || []);
  const { data: groupsData } = useGetGroupsQuery();
  const userGroups = useMemo(
    () => groupsData?.userAccessible ?? [],
    [groupsData],
  );

  useEffect(() => {
    if (!tagOptions || tagOptions.length === 0) {
      dispatch(objectTagsActions.fetchTagOptions());
    }
  }, [dispatch]);

  // Filter tags to only show those the user has access to (via group membership)
  const userGroupIds = useMemo(
    () => new Set((userGroups || []).map((g: any) => g.id)),
    [userGroups],
  );

  const accessibleTags = useMemo(() => {
    if (!source.tags) return [];
    return source.tags.filter((tag) => {
      if (!tag.groups?.length) return true;
      return tag.groups.some((group) => userGroupIds.has(group.id));
    });
  }, [source.tags, userGroupIds]);

  const measureTextWidth = useCallback((text: string) => {
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
  }, []);

  // Calculate how many tags we can put on the container
  const calculateVisibleTags = useCallback(() => {
    if (!accessibleTags?.length || !containerRef.current) {
      return accessibleTags?.length || 0;
    }

    const availableWidth = containerRef.current.offsetWidth;
    let totalWidth = 0;
    let visibleCount = 0;

    for (let i = 0; i < accessibleTags.length; i++) {
      const tagWidth = measureTextWidth(accessibleTags[i]!.name);

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
  }, [accessibleTags, measureTextWidth]);

  useEffect(() => {
    if (!containerRef.current) return undefined;

    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
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
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (!accessibleTags?.length) {
    return null;
  }

  const hasMoreTags = accessibleTags.length > visibleTagsCount;
  const visibleTags = accessibleTags.slice(0, visibleTagsCount);
  const hiddenTags = accessibleTags.slice(visibleTagsCount);

  const visibleTagsWithColors = visibleTags.map((tag) => {
    const tagOption = tagOptions.find(
      (option: any) => option.id === tag.objtagoption_id,
    );
    return {
      ...tag,
      color: tagOption?.color || "#dddfe2",
    };
  });

  const hiddenTagsWithColors = hiddenTags.map((tag) => {
    const tagOption = tagOptions.find(
      (option: any) => option.id === tag.objtagoption_id,
    );
    return {
      ...tag,
      color: tagOption?.color || "#dddfe2",
    };
  });

  return (
    <div className={styles["tagsContainer"]} ref={containerRef}>
      <span
        ref={measureRef}
        style={{ visibility: "hidden", position: "absolute" }}
      />

      {visibleTagsWithColors.map((tag) => (
        <Chip
          key={tag.id}
          label={tag.name}
          size="small"
          className={styles["tagChip"]}
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
            className={styles["tagChip"]}
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

export default DynamicTagDisplay;
