import { useEffect, useState } from "react";
import dayjs from "dayjs";
import calendar from "dayjs/plugin/calendar";

import Grid from "@mui/material/Grid";
import IconButton from "@mui/material/IconButton";
import Button from "@mui/material/Button";
import Tooltip from "@mui/material/Tooltip";
import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";

import Thumbnail from "./Thumbnail";
import { useGenerateSurveyThumbnailMutation } from "../../ducks/candidate/candidates";

dayjs.extend(calendar);

const ALERT_THUMBNAIL_TYPES = ["new", "ref", "sub"];
const ARCHIVAL_THUMBNAIL_TYPES = ["sdss", "ls", "ps1", "sm", "hst", "chandra"];
// PanSTARRS is resolved asynchronously on the backend after the source loads;
// show a loading tile while it arrives. (SkyMapper/HST/Chandra/JWST are
// on-demand, so no loading tile for those.)
const LOADING_PLACEHOLDER_TYPES = ["ps1"];
// On-demand cutouts (loaded via the button, not auto-generated).
const ON_DEMAND_TYPES = ["sm", "hst", "chandra", "jwst"];
// At most this many thumbnails are visible at once; the rest are cycled through.
const MAX_VISIBLE_THUMBNAILS = 3;

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
  useGrid?: boolean | undefined;
  size?: string | undefined;
  minSize?: string | null | undefined;
  maxSize?: string | null | undefined;
  noMargin?: boolean | undefined;
  titleSize?: string | undefined;
  displayTypes?: string[] | undefined;
  // When set, show a control to generate on-demand pointed cutouts (HST/Chandra).
  objID?: string | undefined;
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
  objID = undefined,
}: ThumbnailListProps) => {
  const [offset, setOffset] = useState(0);
  // Types that resolved to "no coverage" client-side (e.g. Legacy Survey blanks);
  // dropped from the display so cycling only shows genuine imagery.
  const [unavailable, setUnavailable] = useState<Set<string>>(() => new Set());
  useEffect(() => setUnavailable(new Set()), [objID]);
  const markUnavailable = (type: string) =>
    setUnavailable((prev) => (prev.has(type) ? prev : new Set(prev).add(type)));
  const [generateSurveyThumbnail, { isLoading: onDemandLoading }] =
    useGenerateSurveyThumbnailMutation();

  const sortedThumbnails = [...(thumbnails ?? [])].sort(sortThumbnailsByDate);
  const latestThumbnails = thumbnailTypes
    .filter((type) => displayTypes.includes(type))
    .map((type) => sortedThumbnails.find((t) => t.type === type))
    .filter(Boolean);

  const archivalThumbnails = latestThumbnails.filter((t) =>
    ARCHIVAL_THUMBNAIL_TYPES.includes(t.type),
  );

  // Ordered tiles to display; append a loading tile for any all-sky archival
  // cutout still being resolved on the backend (mirrors the old PanSTARRS case).
  const tiles: {
    key: string;
    name: string;
    src: string;
    grayscale: boolean;
  }[] = latestThumbnails.map((t) => ({
    key: `${t.id}`,
    name: t.type,
    src: t.public_url,
    grayscale: t.is_grayscale,
  }));
  if (archivalThumbnails.length > 0) {
    LOADING_PLACEHOLDER_TYPES.forEach((type) => {
      if (
        displayTypes.includes(type) &&
        !latestThumbnails.some((t) => t.type === type)
      ) {
        tiles.push({
          key: `${type}-loading`,
          name: type,
          src: "#",
          grayscale: false,
        });
      }
    });
  }

  // Drop placeholder tiles (no coverage, or the cutout service was
  // unavailable) so cycling only shows real cutouts. Loading tiles (src "#")
  // are kept — they resolve to a real image or disappear on refresh.
  const isPlaceholder = (src: string) =>
    src.includes("outside_survey") || src.includes("currently_unavailable");
  const shownTiles = tiles.filter(
    (t) => !isPlaceholder(t.src) && !unavailable.has(t.name),
  );

  const renderTile = (tile: (typeof tiles)[number]) => (
    <Grid key={tile.key}>
      <Thumbnail
        ra={ra}
        dec={dec}
        name={tile.name}
        src={tile.src}
        size={size}
        minSize={minSize ?? size}
        maxSize={maxSize ?? size}
        noMargin={!useGrid && noMargin}
        grayscale={tile.grayscale}
        titleSize={titleSize}
        onUnavailable={() => markUnavailable(tile.name)}
      />
    </Grid>
  );

  // Show at most MAX_VISIBLE_THUMBNAILS at once; cycle through the rest.
  const maxOffset = Math.max(0, shownTiles.length - MAX_VISIBLE_THUMBNAILS);
  const clampedOffset = Math.min(offset, maxOffset);
  const visibleTiles = shownTiles.slice(
    clampedOffset,
    clampedOffset + MAX_VISIBLE_THUMBNAILS,
  );
  const showControls = shownTiles.length > MAX_VISIBLE_THUMBNAILS;

  // On-demand cutouts (SkyMapper/HST/Chandra/JWST): offer a control if we have
  // an objID and no *real* one is loaded yet. Placeholders (no coverage / the
  // service failed) don't count, so the button stays available to retry.
  const hasOnDemand = latestThumbnails.some(
    (t) => ON_DEMAND_TYPES.includes(t.type) && !isPlaceholder(t.public_url),
  );
  const showOnDemandButton = Boolean(objID) && !hasOnDemand;
  const handleLoadOnDemand = () => {
    if (objID) {
      generateSurveyThumbnail({ objID, types: ON_DEMAND_TYPES });
    }
  };

  const items = (
    <>
      {showControls && (
        <Grid>
          <IconButton
            size="small"
            aria-label="previous thumbnails"
            disabled={clampedOffset === 0}
            onClick={() => setOffset(Math.max(0, clampedOffset - 1))}
          >
            <ChevronLeftIcon />
          </IconButton>
        </Grid>
      )}
      {visibleTiles.map(renderTile)}
      {showControls && (
        <Grid>
          <IconButton
            size="small"
            aria-label="next thumbnails"
            disabled={clampedOffset >= maxOffset}
            onClick={() => setOffset(Math.min(maxOffset, clampedOffset + 1))}
          >
            <ChevronRightIcon />
          </IconButton>
        </Grid>
      )}
      {showOnDemandButton && (
        <Grid>
          <Tooltip title="Load SkyMapper, HST, Chandra & JWST cutouts">
            <span>
              <Button
                size="small"
                onClick={handleLoadOnDemand}
                disabled={onDemandLoading}
              >
                {onDemandLoading ? "Loading…" : "Request more thumbnails"}
              </Button>
            </span>
          </Tooltip>
        </Grid>
      )}
    </>
  );

  if (!useGrid) return items;

  return (
    <Grid
      container
      direction="row"
      spacing={1}
      sx={{ flexWrap: "nowrap", alignItems: "center" }}
    >
      {items}
    </Grid>
  );
};

export default ThumbnailList;
