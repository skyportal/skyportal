import { useEffect, useState } from "react";
import dayjs from "dayjs";

import Box from "@mui/material/Box";
import Grid from "@mui/material/Grid";
import Button from "@mui/material/Button";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Tooltip from "@mui/material/Tooltip";

import Thumbnail from "./Thumbnail";
import { useGenerateSurveyThumbnailMutation } from "../../ducks/candidate/candidates";

const ALERT_THUMBNAIL_TYPES = ["new", "ref", "sub"];
const ARCHIVAL_THUMBNAIL_TYPES = [
  "sdss",
  "ls",
  "ps1",
  "sm",
  "hst",
  "chandra",
  "jwst",
];
const ON_DEMAND_TYPES = ["sm", "hst", "chandra", "jwst"];
const FETCHED_TYPES = ["sdss", "ls"];
const MAXIMUM_NB_OF_RETRIES = 3;
const MAX_VISIBLE_THUMBNAILS = 3;
const thumbnailTypes = [...ALERT_THUMBNAIL_TYPES, ...ARCHIVAL_THUMBNAIL_TYPES];
const SURVEY_FIELD_OF_VIEW_ARCSEC: Record<string, number> = {
  ZTF: 64,
  LSST: 6,
};

const formatFieldOfView = (arcsec: number) =>
  arcsec >= 60 ? `${Math.round(arcsec / 60)}′` : `${arcsec}″`;

export const isPlaceholder = (src?: string | null) =>
  !src ||
  src.includes("outside_survey") ||
  src.includes("currently_unavailable");

interface Tile {
  key: string;
  name: string;
  survey?: string | undefined;
  detail?: string | undefined;
  fieldOfView?: number | undefined;
  message?: string | undefined;
  src: string;
  grayscale: boolean;
}

interface TileGroup {
  key: string;
  label: string;
  tiles: Tile[];
}

interface Block {
  group: TileGroup;
  tiles: Tile[];
}

const toTile = (t: any): Tile => ({
  key: `${t.id}`,
  name: t.type,
  src: t.public_url,
  grayscale: t.is_grayscale,
});

const timestamp = (t: any) => {
  const stamp = t.modified ?? t.created_at;
  return stamp ? dayjs(stamp) : null;
};

const latestTimestamp = (thumbnails: any[]) =>
  thumbnails
    .map(timestamp)
    .reduce((a, b) => (a && (!b || a.isAfter(b)) ? a : b), null);

const alertTile = (t: any): Tile => ({
  ...toTile(t),
  survey: t.survey ?? undefined,
  detail: t.type === "new" ? timestamp(t)?.format("YYYY-MM-DD") : undefined,
  fieldOfView: SURVEY_FIELD_OF_VIEW_ARCSEC[t.survey ?? ""],
});

const alertGroups = (sortedThumbnails: any[], objID?: string) => {
  const bySurvey = new Map<string, any[]>();
  sortedThumbnails
    .filter((t) => ALERT_THUMBNAIL_TYPES.includes(t.type))
    .forEach((t) => {
      const survey = t.survey ?? "";
      const group = bySurvey.get(survey) ?? [];
      if (!group.some((g) => g.type === t.type)) {
        bySurvey.set(survey, [...group, t]);
      }
    });

  return [...bySurvey.entries()]
    .map(([survey, group]) => ({
      survey,
      group,
      own: group.some((t) => t.obj_id === objID),
      updated: latestTimestamp(group),
    }))
    .sort(
      (a, b) =>
        Number(b.own) - Number(a.own) ||
        (b.updated?.valueOf() ?? 0) - (a.updated?.valueOf() ?? 0),
    )
    .map(({ survey, group }): TileGroup => ({
      key: survey || "alert",
      label: survey || "Alert",
      tiles: ALERT_THUMBNAIL_TYPES.flatMap((type) =>
        group.filter((t) => t.type === type),
      ).map(alertTile),
    }));
};

const packRows = (groups: TileGroup[], perRow: number) => {
  const rows: Block[][] = [];
  let used = perRow;
  groups.forEach((group) => {
    for (let i = 0; i < group.tiles.length; i += perRow) {
      const tiles = group.tiles.slice(i, i + perRow);
      if (used + tiles.length > perRow) {
        rows.push([]);
        used = 0;
      }
      rows[rows.length - 1]!.push({ group, tiles });
      used += tiles.length;
    }
  });
  return rows;
};

const pageLabels = (pages: Block[][][]) => {
  const labels = pages.map((page) =>
    [...new Set(page.flat().map((block) => block.group.label))].join(" · "),
  );
  return labels.map((label, i) => {
    const count = labels.filter((l) => l === label).length;
    if (count === 1) return label;
    return `${label} ${labels.slice(0, i + 1).filter((l) => l === label).length}`;
  });
};

interface FetchedCutout {
  url?: string;
  message?: string;
  unavailable?: boolean;
}

const fetchCutout = async (
  src: string,
  name: string,
  signal: AbortSignal,
  retry = 0,
): Promise<FetchedCutout> => {
  const response = await fetch(src, { signal });
  if (response.status === 429) {
    if (retry >= MAXIMUM_NB_OF_RETRIES) return { message: "Too Many Requests" };
    await new Promise((resolve) => setTimeout(resolve, 2000));
    return fetchCutout(src, name, signal, retry + 1);
  }
  if (
    response.status === 404 &&
    response.statusText.includes("(ra, dec) is outside")
  ) {
    return { unavailable: true };
  }
  if (!response.ok) return { message: "Currently Unavailable" };
  const blob = await response.blob();
  // Legacy Survey answers outside its footprint with a small grey placeholder.
  if (name === "ls" && blob.size < 1500) return { unavailable: true };
  return { url: URL.createObjectURL(blob) };
};

const useFetchedCutouts = (thumbnails: any[]) => {
  const requests = JSON.stringify(
    thumbnails
      .filter(
        (t) => FETCHED_TYPES.includes(t.type) && !isPlaceholder(t.public_url),
      )
      .map((t) => [`${t.id}`, t.type, t.public_url]),
  );
  const [results, setResults] = useState<Record<string, FetchedCutout>>({});

  useEffect(() => {
    const controller = new AbortController();
    const urls: string[] = [];
    setResults({});
    (JSON.parse(requests) as [string, string, string][]).forEach(
      ([key, name, src]) => {
        fetchCutout(src, name, controller.signal)
          .catch((): FetchedCutout => ({ message: "Currently Unavailable" }))
          .then((result) => {
            if (controller.signal.aborted) {
              if (result.url) URL.revokeObjectURL(result.url);
              return;
            }
            if (result.url) urls.push(result.url);
            setResults((prev) => ({ ...prev, [key]: result }));
          });
      },
    );
    return () => {
      controller.abort();
      urls.forEach((url) => URL.revokeObjectURL(url));
    };
  }, [requests]);

  return results;
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
  objID?: string | undefined;
  columns?: number | undefined;
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
  columns = undefined,
}: ThumbnailListProps) => {
  const [pageIndex, setPageIndex] = useState(0);
  const [sameScale, setSameScale] = useState(false);
  useEffect(() => setPageIndex(0), [objID]);
  const [generateSurveyThumbnail, { isLoading: onDemandLoading }] =
    useGenerateSurveyThumbnailMutation();

  const sortedThumbnails = [...(thumbnails ?? [])]
    .filter((t) => displayTypes.includes(t.type))
    .sort((a, b) => dayjs(b.created_at).diff(a.created_at));

  const latestArchival = ARCHIVAL_THUMBNAIL_TYPES.flatMap((type) =>
    sortedThumbnails.filter((t) => t.type === type).slice(0, 1),
  );
  const fetched = useFetchedCutouts(latestArchival);
  const archivalTiles = latestArchival.flatMap((t): Tile[] => {
    if (!FETCHED_TYPES.includes(t.type)) return [toTile(t)];
    const result = fetched[`${t.id}`];
    if (!result || result.unavailable) return [];
    return [
      {
        ...toTile(t),
        src: result.url ?? t.public_url,
        message: result.message,
      },
    ];
  });

  const groups = [
    ...alertGroups(sortedThumbnails, objID),
    { key: "archival", label: "Archival", tiles: archivalTiles },
  ]
    .map((group) => ({
      ...group,
      tiles: group.tiles.filter((t) => !isPlaceholder(t.src)),
    }))
    .filter((group) => group.tiles.length > 0);

  const preload = JSON.stringify(
    groups
      .flatMap((group) => group.tiles.map((t) => t.src))
      .filter((src) => !src.startsWith("blob:") && !src.startsWith("data:")),
  );
  useEffect(() => {
    (JSON.parse(preload) as string[]).forEach((src) => {
      new Image().src = src;
    });
  }, [preload]);

  const perRow = columns ?? MAX_VISIBLE_THUMBNAILS;
  const rowsPerPage = columns ? 2 : 1;
  const rows = packRows(groups, perRow);
  const pages: Block[][][] = [];
  for (let i = 0; i < rows.length; i += rowsPerPage) {
    pages.push(rows.slice(i, i + rowsPerPage));
  }
  const currentPage = Math.min(pageIndex, Math.max(0, pages.length - 1));
  const track = columns ? "minmax(0, 1fr)" : "max-content";

  const fieldsOfView = [
    ...new Set(
      groups.flatMap((group) => group.tiles.map((t) => t.fieldOfView ?? 0)),
    ),
  ].filter(Boolean);
  const widestFieldOfView = Math.max(...fieldsOfView);
  const scaleMatched = sameScale && fieldsOfView.length > 1;

  const showOnDemandButton =
    Boolean(objID) &&
    !latestArchival.some(
      (t) => ON_DEMAND_TYPES.includes(t.type) && !isPlaceholder(t.public_url),
    );

  const renderTile = (tile: Tile) => (
    <Thumbnail
      ra={ra}
      dec={dec}
      name={tile.name}
      survey={tile.survey}
      detail={tile.detail}
      fieldOfView={
        tile.fieldOfView
          ? formatFieldOfView(
              scaleMatched ? widestFieldOfView : tile.fieldOfView,
            )
          : undefined
      }
      zoom={
        scaleMatched && tile.fieldOfView
          ? tile.fieldOfView / widestFieldOfView
          : 1
      }
      src={tile.src}
      size={size}
      minSize={minSize ?? size}
      maxSize={maxSize ?? size}
      noMargin={!useGrid && noMargin}
      grayscale={tile.grayscale}
      titleSize={titleSize}
      message={tile.message}
    />
  );

  const onDemandButton = (
    <Tooltip title="Load SkyMapper, HST, Chandra & JWST cutouts">
      <span>
        <Button
          size="small"
          onClick={() =>
            objID && generateSurveyThumbnail({ objID, types: ON_DEMAND_TYPES })
          }
          disabled={onDemandLoading}
        >
          {onDemandLoading ? "Loading…" : "Request more thumbnails"}
        </Button>
      </span>
    </Tooltip>
  );

  const content = (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
      {(pages.length > 1 || fieldsOfView.length > 1) && (
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            ...(pages.length > 1 && {
              borderBottom: 1,
              borderColor: "divider",
            }),
          }}
        >
          {pages.length > 1 && (
            <Tabs
              value={currentPage}
              onChange={(_, value) => setPageIndex(value)}
              variant="fullWidth"
              sx={{
                flex: 1,
                minHeight: "auto",
                "& .MuiTab-root": {
                  minHeight: "auto",
                  padding: "0.4rem 0.75rem",
                  fontSize: "0.8rem",
                  fontWeight: "bold",
                  textTransform: "none",
                },
              }}
            >
              {pageLabels(pages).map((label) => (
                <Tab key={label} label={label} />
              ))}
            </Tabs>
          )}
          {fieldsOfView.length > 1 && (
            <Tooltip
              title={`Show every alert cutout at the ${formatFieldOfView(widestFieldOfView)} field of view`}
            >
              <FormControlLabel
                control={
                  <Switch
                    size="small"
                    checked={sameScale}
                    onChange={(event) => setSameScale(event.target.checked)}
                  />
                }
                label="Same scale"
                sx={{
                  marginLeft: "auto",
                  marginRight: 0,
                  paddingLeft: 1,
                  whiteSpace: "nowrap",
                  "& .MuiFormControlLabel-label": { fontSize: "0.8rem" },
                }}
              />
            </Tooltip>
          )}
        </Box>
      )}
      <Box
        sx={{
          display: "grid",
          gap: 1,
          gridTemplateColumns: `repeat(${perRow}, ${track})`,
        }}
      >
        {(pages[currentPage] ?? []).flatMap((row, rowIndex) =>
          row
            .flatMap((block) => block.tiles)
            .map((tile, columnIndex) => (
              <Box
                key={tile.key}
                sx={{
                  gridRow: rowIndex + 1,
                  gridColumn: columnIndex + 1,
                  minWidth: 0,
                }}
              >
                {renderTile(tile)}
              </Box>
            )),
        )}
      </Box>
      {showOnDemandButton && <div>{onDemandButton}</div>}
    </Box>
  );

  if (!useGrid && !columns) return <Grid>{content}</Grid>;
  return content;
};

export default ThumbnailList;
