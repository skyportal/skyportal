import { useMemo, useState } from "react";
import { Link as RouterLink } from "react-router-dom";

import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import utc from "dayjs/plugin/utc";

import Box from "@mui/material/Box";
import ButtonBase from "@mui/material/ButtonBase";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import IconButton from "@mui/material/IconButton";
import Link from "@mui/material/Link";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import VisibilityIcon from "@mui/icons-material/Visibility";
import VisibilityOffIcon from "@mui/icons-material/VisibilityOff";

import Button from "../Button";
import Paper from "../Paper";
import UserAvatar, { getUserRealName } from "./UserAvatar";
import { isPlaceholder } from "../thumbnail/ThumbnailList";
import {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
} from "../../ducks/profile";
import { useGetUserActivityInfiniteQuery } from "../../ducks/users";
import type {
  ActivityItem,
  ActivityKind,
  ActivityObj,
  PublicProfile,
} from "../../ducks/users";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const ACTIVITY_LABELS: [ActivityKind, string][] = [
  ["sources_saved", "Sources saved"],
  ["classifications", "Classifications"],
  ["comments", "Comments"],
  ["annotations", "Annotations"],
  ["spectra", "Spectra"],
  ["followup_requests", "Follow-up requests"],
];

const ACTIVITY_VERBS: Record<ActivityKind, string> = {
  sources_saved: "saved",
  classifications: "classified",
  comments: "commented on",
  annotations: "annotated",
  spectra: "uploaded a spectrum of",
  followup_requests: "requested follow-up of",
};

const TILE = {
  flex: "0 1 calc((100% - 12px) / 4)",
  minWidth: 0,
  maxWidth: 240,
  aspectRatio: "1",
  borderRadius: 1,
  display: "block",
  bgcolor: "action.hover",
};

interface ActivityGroup {
  newest: ActivityItem;
  items: ActivityItem[];
}

interface ActivityDay {
  day: string;
  groups: ActivityGroup[];
}

const localTime = (createdAt: string) => dayjs.utc(`${createdAt}Z`).local();

const groupByDay = (items: ActivityItem[]) =>
  items.reduce<ActivityDay[]>((days, item) => {
    const day = localTime(item.created_at).format("YYYY-MM-DD");
    let current = days[days.length - 1];
    if (!current || current.day !== day) {
      current = { day, groups: [] };
      days.push(current);
    }
    const group = current.groups[current.groups.length - 1];
    if (group && item.obj_id && group.newest.obj_id === item.obj_id) {
      group.items.push(item);
    } else {
      current.groups.push({ newest: item, items: [item] });
    }
    return days;
  }, []);

const dayLabel = (day: string) => {
  const date = dayjs(day);
  if (date.isSame(dayjs(), "day")) return "Today";
  if (date.isSame(dayjs().subtract(1, "day"), "day")) return "Yesterday";
  return date.format(
    date.isSame(dayjs(), "year") ? "dddd, MMMM D" : "MMMM D, YYYY",
  );
};

const joinVerbs = (items: ActivityItem[]) => {
  const verbs = [...new Set(items.map((item) => ACTIVITY_VERBS[item.kind]))];
  if (verbs.length === 1) return verbs[0];
  return `${verbs.slice(0, -1).join(", ")} and ${verbs[verbs.length - 1]}`;
};

interface LightCurveProps {
  points: [number, number, string][];
  colors: Record<string, string>;
}

const LightCurve = ({ points, colors }: LightCurveProps) => {
  const mjds = points.map(([mjd]) => mjd);
  const mags = points.map(([, mag]) => mag);
  const [x0, x1] = [Math.min(...mjds), Math.max(...mjds)];
  const [y0, y1] = [Math.min(...mags), Math.max(...mags)];
  const x = (mjd: number) =>
    x1 > x0 ? 20 + (74 * (mjd - x0)) / (x1 - x0) : 57;
  const y = (mag: number) => (y1 > y0 ? 8 + (72 * (mag - y0)) / (y1 - y0) : 44);
  const bands = [...new Set(points.map(([, , band]) => band))];
  const date = (mjd: number) =>
    dayjs((mjd - 40587) * 86400000).format(
      x1 - x0 > 365 ? "MMM YYYY" : "MMM D",
    );

  return (
    <Box sx={{ ...TILE, color: "text.secondary" }}>
      <svg
        viewBox="0 0 100 100"
        width="100%"
        height="100%"
        style={{ display: "block" }}
      >
        {(y1 > y0 ? [y0, y1] : [y0]).map((mag) => (
          <line
            key={mag}
            x1={17}
            x2={97}
            y1={y(mag)}
            y2={y(mag)}
            stroke="currentColor"
            strokeOpacity={0.25}
            strokeWidth={0.5}
          />
        ))}
        <path
          d="M17 4 V86 H97"
          fill="none"
          stroke="currentColor"
          strokeOpacity={0.6}
          strokeWidth={0.6}
        />
        <g fill="currentColor" fontSize={6} textAnchor="end">
          <text x={15} y={y(y0) + 2}>
            {y0.toFixed(1)}
          </text>
          {y1 > y0 && (
            <text x={15} y={y(y1) + 2}>
              {y1.toFixed(1)}
            </text>
          )}
          {date(x1) === date(x0) ? (
            <text x={57} y={95} textAnchor="middle">
              {date(x0)}
            </text>
          ) : (
            <>
              <text x={17} y={95} textAnchor="start">
                {date(x0)}
              </text>
              <text x={97} y={95}>
                {date(x1)}
              </text>
            </>
          )}
        </g>
        {bands.map((band) => (
          <polyline
            key={band}
            points={points
              .filter(([, , b]) => b === band)
              .map(([mjd, mag]) => `${x(mjd)},${y(mag)}`)
              .join(" ")}
            fill="none"
            stroke={colors[band] ?? "#888"}
            strokeOpacity={0.6}
            strokeWidth={0.7}
          />
        ))}
        {points.map(([mjd, mag, band], index) => (
          <circle
            key={index}
            cx={x(mjd)}
            cy={y(mag)}
            r={1.6}
            fill={colors[band] ?? "#888"}
          />
        ))}
      </svg>
    </Box>
  );
};

interface MediaProps {
  objId: string;
  obj: ActivityObj;
  colors: Record<string, string>;
}

const Media = ({ objId, obj, colors }: MediaProps) => {
  const [failed, setFailed] = useState<string[]>([]);
  const invert = useGetProfileQuery().data?.preferences?.["invertThumbnails"];
  const stamps = obj.thumbnails
    .filter(
      (t) => !isPlaceholder(t.public_url) && !failed.includes(t.public_url),
    )
    .slice(0, 3);
  const curve = obj.photometry.length > 1;
  if (!stamps.length && !curve) return null;

  return (
    <Link
      component={RouterLink}
      to={`/source/${objId}`}
      sx={{ display: "flex", gap: 0.5, mt: 1 }}
    >
      {stamps.map((t) => (
        <Box
          key={t.public_url}
          component="img"
          src={t.public_url}
          alt={`${objId} ${t.type}`}
          loading="lazy"
          onError={() => setFailed((urls) => [...urls, t.public_url])}
          sx={{
            ...TILE,
            objectFit: "cover",
            filter: invert && t.is_grayscale ? "invert(1)" : undefined,
          }}
        />
      ))}
      {curve && <LightCurve points={obj.photometry} colors={colors} />}
    </Link>
  );
};

const Comments = ({ items }: { items: ActivityItem[] }) => (
  <Box
    sx={{
      display: "flex",
      flexDirection: "column",
      alignItems: "flex-start",
      gap: 0.75,
      mt: 1,
    }}
  >
    {items.map((item) => (
      <Box
        key={item.created_at}
        sx={{
          bgcolor: "action.hover",
          borderRadius: 3,
          px: 1.5,
          py: 0.75,
          maxWidth: "100%",
        }}
      >
        <Typography variant="body2" sx={{ overflowWrap: "anywhere" }}>
          {item.detail}
        </Typography>
      </Box>
    ))}
  </Box>
);

const Tags = ({ items }: { items: ActivityItem[] }) => {
  const tags = items.filter((item) => item.detail);
  if (!tags.length) return null;
  return (
    <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, mt: 1 }}>
      {tags.map((item) => (
        <Chip
          key={`${item.kind}-${item.created_at}`}
          size="small"
          variant="outlined"
          label={item.detail}
        />
      ))}
    </Box>
  );
};

interface PostProps {
  user: PublicProfile;
  group: ActivityGroup;
  obj: ActivityObj | undefined;
  colors: Record<string, string>;
  collapsed: boolean;
}

const Post = ({ user, group, obj, colors, collapsed }: PostProps) => {
  const { newest } = group;
  const objId = newest.obj_id;
  const time = localTime(newest.created_at);
  const comments = group.items.filter((item) => item.kind === "comments");

  return (
    <Box>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
        <UserAvatar
          size={40}
          firstName={user.first_name}
          lastName={user.last_name}
          username={user.username}
          gravatarUrl={user.gravatar_url}
          isBot={user.is_bot}
          noTooltip
        />
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="body2">
            <Box component="span" sx={{ fontWeight: 600 }}>
              {getUserRealName(user.first_name, user.last_name) ||
                user.username}
            </Box>{" "}
            {joinVerbs(group.items)}{" "}
            {objId && (
              <Link
                component={RouterLink}
                to={`/source/${objId}`}
                sx={{ fontWeight: 600 }}
              >
                {objId}
              </Link>
            )}
          </Typography>
          <Tooltip title={time.format("YYYY-MM-DD HH:mm")}>
            <Typography variant="caption" color="textSecondary">
              {time.fromNow()}
            </Typography>
          </Tooltip>
        </Box>
      </Box>
      {!collapsed &&
        (comments.length ? (
          <Comments items={comments} />
        ) : (
          <>
            <Tags items={group.items} />
            {objId && obj && <Media objId={objId} obj={obj} colors={colors} />}
          </>
        ))}
    </Box>
  );
};

interface FeedProps {
  user: PublicProfile;
  kind: ActivityKind | null;
  collapsed: boolean;
}

const Feed = ({ user, kind, collapsed }: FeedProps) => {
  const { data, hasNextPage, fetchNextPage, isFetchingNextPage } =
    useGetUserActivityInfiniteQuery({ id: user.id, kind });
  const days = useMemo(
    () => groupByDay((data?.pages ?? []).flatMap((page) => page.items)),
    [data],
  );
  if (!data) {
    return (
      <Button secondary size="small" disabled sx={{ alignSelf: "center" }}>
        Loading...
      </Button>
    );
  }

  const objs = Object.assign({}, ...data.pages.map((page) => page.objs));
  const colors = Object.assign(
    {},
    ...data.pages.map((page) => page.filter_colors),
  );
  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
      {days.map(({ day, groups }) => (
        <Box key={day}>
          <Divider sx={{ mb: 1 }}>
            <Typography variant="caption" color="textSecondary">
              {dayLabel(day)}
            </Typography>
          </Divider>
          <Paper
            sx={{
              display: "flex",
              flexDirection: "column",
              gap: collapsed ? 1.5 : 2.5,
            }}
          >
            {groups.map((group) => (
              <Post
                key={`${group.newest.kind}-${group.newest.obj_id}-${group.newest.created_at}`}
                user={user}
                group={group}
                obj={
                  group.newest.obj_id ? objs[group.newest.obj_id] : undefined
                }
                colors={colors}
                collapsed={collapsed}
              />
            ))}
          </Paper>
        </Box>
      ))}
      {hasNextPage && (
        <Button
          secondary
          size="small"
          disabled={isFetchingNextPage}
          onClick={() => fetchNextPage()}
          sx={{ alignSelf: "center" }}
        >
          {isFetchingNextPage ? "Loading..." : "Show more"}
        </Button>
      )}
    </Box>
  );
};

interface VisibilityToggleProps {
  shown: boolean;
  label: string;
  onToggle: () => void;
}

const VisibilityToggle = ({
  shown,
  label,
  onToggle,
}: VisibilityToggleProps) => (
  <Tooltip
    placement="right"
    title={
      shown ? "Shown on your public profile" : "Hidden from your public profile"
    }
  >
    <IconButton
      size="small"
      aria-label={`Toggle ${label} on public profile`}
      onClick={onToggle}
      sx={{ p: 0.25, color: "text.secondary" }}
    >
      {shown ? (
        <VisibilityIcon fontSize="small" />
      ) : (
        <VisibilityOffIcon fontSize="small" />
      )}
    </IconButton>
  </Tooltip>
);

interface ContributionsProps {
  counts: Record<ActivityKind, number>;
  owner: boolean;
  selected: ActivityKind | null;
  onSelect: (kind: ActivityKind | null) => void;
  collapsed: boolean;
  onCollapse: () => void;
}

const Contributions = ({
  counts,
  owner,
  selected,
  onSelect,
  collapsed,
  onCollapse,
}: ContributionsProps) => {
  const publicProfile =
    useGetProfileQuery().data?.preferences?.["publicProfile"] ?? {};
  const [updatePreferences] = useUpdateUserPreferencesMutation();
  const shown = (key: string) => publicProfile[key] ?? true;
  const toggle = (key: string) =>
    updatePreferences({ publicProfile: { [key]: !shown(key) } });

  const rows = ACTIVITY_LABELS.filter(([key]) => counts[key] > 0).map(
    ([key, label]) => ({ key, label, count: counts[key] }),
  );
  const total = rows.reduce((sum, row) => sum + row.count, 0);

  return (
    <Paper sx={{ px: 1, position: { md: "sticky" }, top: { md: 80 } }}>
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          px: 1,
          mb: 0.5,
        }}
      >
        <Typography variant="subtitle2">Contributions</Typography>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          {rows.length > 0 && (
            <Link
              component="button"
              variant="caption"
              color="textSecondary"
              underline="hover"
              onClick={onCollapse}
            >
              {collapsed ? "Expand all" : "Collapse all"}
            </Link>
          )}
          {owner && (
            <VisibilityToggle
              shown={shown("activity")}
              label="activity"
              onToggle={() => toggle("activity")}
            />
          )}
        </Box>
      </Box>
      {rows.length === 0 ? (
        <Typography variant="body2" color="textSecondary" sx={{ px: 1 }}>
          Nothing you have access to see.
        </Typography>
      ) : (
        [{ key: null, label: "All", count: total }, ...rows].map(
          ({ key, label, count }) => {
            const active = selected === key;
            const hidden =
              owner &&
              (!shown("activity") ||
                (key !== null && !shown(`activity_${key}`)));
            return (
              <Box
                key={key ?? "all"}
                sx={{ display: "flex", alignItems: "center", gap: 0.5 }}
              >
                <ButtonBase
                  onClick={() => onSelect(key)}
                  sx={{
                    display: "flex",
                    justifyContent: "space-between",
                    flexGrow: 1,
                    px: 1,
                    py: 0.5,
                    borderRadius: 1,
                    opacity: hidden ? 0.5 : 1,
                    bgcolor: active ? "action.selected" : "transparent",
                    "&:hover": {
                      bgcolor: active ? "action.selected" : "action.hover",
                    },
                  }}
                >
                  <Typography
                    variant="body2"
                    color={active ? "textPrimary" : "textSecondary"}
                    sx={{ fontWeight: active ? 600 : 400 }}
                  >
                    {label}
                  </Typography>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>
                    {count.toLocaleString()}
                  </Typography>
                </ButtonBase>
                {owner &&
                  (key === null ? (
                    <Box sx={{ width: 24, flexShrink: 0 }} />
                  ) : (
                    <VisibilityToggle
                      shown={shown(`activity_${key}`)}
                      label={label}
                      onToggle={() => toggle(`activity_${key}`)}
                    />
                  ))}
              </Box>
            );
          },
        )
      )}
    </Paper>
  );
};

const ProfileActivity = ({ user }: { user: PublicProfile }) => {
  const [kind, setKind] = useState<ActivityKind | null>(null);
  const [collapsed, setCollapsed] = useState(false);
  const { data } = useGetUserActivityInfiniteQuery({ id: user.id, kind: null });
  const owner = useGetProfileQuery().data?.id === user.id;
  const counts = data?.pages[0]?.counts;
  if (!counts) return null;

  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: {
          xs: "minmax(0, 1fr)",
          md: "300px minmax(0, 1fr)",
        },
        alignItems: "start",
        gap: 2,
        mt: 2,
      }}
    >
      <Contributions
        counts={counts}
        owner={owner}
        selected={kind}
        onSelect={setKind}
        collapsed={collapsed}
        onCollapse={() => setCollapsed(!collapsed)}
      />
      {Object.values(counts).some((count) => count > 0) && (
        <Feed user={user} kind={kind} collapsed={collapsed} />
      )}
    </Box>
  );
};

export default ProfileActivity;
