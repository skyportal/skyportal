import React from "react";

import dayjs from "dayjs";
import calendar from "dayjs/plugin/calendar";

import Grid from "@mui/material/Grid";

import Thumbnail from "./Thumbnail";

dayjs.extend(calendar);

const ALERT_THUMBNAIL_TYPES = ["new", "ref", "sub"];
const ARCHIVAL_THUMBNAIL_TYPES = ["sdss", "ls", "ps1"];

const thumbnailTypes = [...ALERT_THUMBNAIL_TYPES, ...ARCHIVAL_THUMBNAIL_TYPES];

const sortThumbnailsByDate = (a: any, b: any) => {
  const aDate = dayjs(a.created_at);
  const bDate = dayjs(b.created_at);
  if (aDate.isAfter(bDate)) {
    return -1;
  }
  if (aDate.isBefore(bDate)) {
    return 1;
  }
  return 0;
};

interface ThumbnailListProps {
  ra: number;
  dec: number;
  thumbnails: any[];
  useGrid?: boolean;
  size?: string;
  minSize?: string | null;
  maxSize?: string | null;
  noMargin?: boolean;
  titleSize?: string;
  displayTypes?: string[];
}

const ThumbnailList = ({
  ra,
  dec,
  thumbnails,
  useGrid = true,
  size = "13rem",
  minSize = null,
  maxSize = null,
  noMargin = false,
  titleSize = "0.875rem",
  displayTypes = thumbnailTypes,
}: ThumbnailListProps) => {
  const sortedThumbnails = [...(thumbnails ?? [])].sort(sortThumbnailsByDate);
  const latestThumbnails = thumbnailTypes
    .filter((type) => displayTypes.includes(type))
    .map((type) => sortedThumbnails.find((t) => t.type === type))
    .filter(Boolean);

  const archivalThumbnails = latestThumbnails.filter((t) =>
    ARCHIVAL_THUMBNAIL_TYPES.includes(t.type),
  );

  // If PanSTARRS DR2 is included in the display types and there are archival thumbnails
  // but none of them are PanSTARRS, show a loading thumbnail for PanSTARRS DR2
  const ps1Loading =
    displayTypes.includes("ps1") &&
    archivalThumbnails.length > 0 &&
    !archivalThumbnails.some((t) => t.type === "ps1");

  const thumbnailItems = (
    <>
      {latestThumbnails.map((t) => (
        <Grid key={t.id}>
          <Thumbnail
            ra={ra}
            dec={dec}
            name={t.type}
            src={t.public_url}
            size={size}
            minSize={minSize ?? size}
            maxSize={maxSize ?? size}
            noMargin={!useGrid && noMargin}
            grayscale={t.is_grayscale}
            titleSize={titleSize}
          />
        </Grid>
      ))}
      {ps1Loading && (
        <Grid>
          <Thumbnail
            ra={ra}
            dec={dec}
            name="ps1"
            src="#"
            size={size}
            minSize={minSize ?? size}
            maxSize={maxSize ?? size}
            noMargin={!useGrid && noMargin}
            grayscale={false}
            titleSize={titleSize}
          />
        </Grid>
      )}
    </>
  );

  if (!useGrid) return thumbnailItems;

  return (
    <Grid container direction="row" spacing={1}>
      {thumbnailItems}
    </Grid>
  );
};

export default ThumbnailList;
