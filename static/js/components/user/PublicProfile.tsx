import { useState } from "react";
import { Link as RouterLink, useNavigate } from "react-router-dom";

import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import utc from "dayjs/plugin/utc";

import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Link from "@mui/material/Link";
import Typography from "@mui/material/Typography";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import ChatIcon from "@mui/icons-material/ChatOutlined";

import Button from "../Button";
import Paper from "../Paper";
import Spinner from "../Spinner";
import UserAvatar, { getUserRealName } from "./UserAvatar";
import withRouter from "../withRouter";
import { chips, field, memberSince } from "./ProfileFields";
import { useGetProfileQuery } from "../../ducks/profile";
import {
  useGetUserActivityQuery,
  useGetUserPublicProfileQuery,
} from "../../ducks/users";
import { useStartDiscussionMutation } from "../../ducks/discussions";

dayjs.extend(relativeTime);
dayjs.extend(utc);
import type { ActivityItem, ActivityKind } from "../../ducks/users";

const PAGE = 25;

// Ordered as a scanner would read them: what was found, then what was said
// about it, then what was asked for.
const ACTIVITY_LABELS: [ActivityKind, string][] = [
  ["sources_saved", "sources saved"],
  ["classifications", "classifications"],
  ["comments", "comments"],
  ["annotations", "annotations"],
  ["spectra", "spectra"],
  ["followup_requests", "follow-up requests"],
];

const ACTIVITY_VERBS: Record<ActivityKind, string> = {
  sources_saved: "Saved",
  classifications: "Classified",
  comments: "Commented on",
  annotations: "Annotated",
  spectra: "Uploaded a spectrum of",
  followup_requests: "Requested follow-up of",
};

const ActivityLine = ({ item }: { item: ActivityItem }) => {
  const verb = ACTIVITY_VERBS[item.kind];
  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "baseline",
        gap: 1,
        py: 0.75,
        borderBottom: 1,
        borderColor: "divider",
      }}
    >
      <Typography variant="body2" sx={{ flexGrow: 1, minWidth: 0 }}>
        {verb}{" "}
        {item.obj_id && (
          <Link component={RouterLink} to={`/source/${item.obj_id}`}>
            {item.obj_id}
          </Link>
        )}
        {item.detail && (
          <Typography
            component="span"
            variant="body2"
            color="textSecondary"
            sx={{ ml: 0.5 }}
          >
            {item.detail}
          </Typography>
        )}
      </Typography>
      <Typography variant="caption" color="textSecondary" noWrap>
        {dayjs.utc(`${item.created_at}Z`).fromNow()}
      </Typography>
    </Box>
  );
};

const Activity = ({ id }: { id: string }) => {
  const [pages, setPages] = useState(1);
  const { data, isFetching } = useGetUserActivityQuery({
    id,
    limit: PAGE * pages,
  });
  if (!data) return null;

  const counts = ACTIVITY_LABELS.filter(([key]) => data.counts[key] > 0);
  return (
    <Box sx={{ mt: 2 }}>
      <Typography variant="subtitle2" gutterBottom>
        Contributions
      </Typography>
      {counts.length === 0 ? (
        <Typography variant="body2" color="textSecondary">
          Nothing you have access to see.
        </Typography>
      ) : (
        <>
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, mb: 1.5 }}>
            {counts.map(([key, label]) => (
              <Chip
                key={key}
                size="small"
                label={`${data.counts[key].toLocaleString()} ${label}`}
              />
            ))}
          </Box>
          {data.items.map((item, index) => (
            <ActivityLine
              key={`${item.kind}-${item.obj_id}-${item.created_at}-${index}`}
              item={item}
            />
          ))}
          {data.has_more && (
            <Button
              secondary
              size="small"
              disabled={isFetching}
              onClick={() => setPages((n) => n + 1)}
              sx={{ mt: 1 }}
            >
              {isFetching ? "Loading..." : "Show more"}
            </Button>
          )}
        </>
      )}
    </Box>
  );
};

interface PublicProfileProps {
  route?: { id: string } | undefined;
}

const PublicProfile = ({ route }: PublicProfileProps) => {
  const id = route?.id;
  const { data: profile, isError } = useGetUserPublicProfileQuery(id!, {
    skip: !id,
  });
  const currentUser = useGetProfileQuery().data;
  const currentUserId = currentUser?.id;
  const navigate = useNavigate();
  const [startDiscussion, { isLoading: starting }] =
    useStartDiscussionMutation();

  if (isError) return <div>Cannot find this user.</div>;
  if (!profile) return <Spinner />;

  return (
    <>
      {currentUserId === profile.id && (
        <Button
          secondary
          size="small"
          component={RouterLink}
          to="/profile"
          data-testid="profile-settings-view"
          sx={{ mb: 0.5 }}
        >
          <ArrowBackIcon fontSize="small" sx={{ mr: 0.5 }} />
          settings
        </Button>
      )}
      <Paper>
        <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
          <UserAvatar
            size={128}
            firstName={profile.first_name}
            lastName={profile.last_name}
            username={profile.username}
            gravatarUrl={profile.gravatar_url}
            isBot={profile.is_bot}
            noTooltip
          />
          <Box sx={{ flexGrow: 1 }}>
            <Typography variant="h5" id="publicProfileRealname">
              {getUserRealName(profile.first_name, profile.last_name)}
            </Typography>
            <Typography variant="subtitle1" color="textSecondary">
              @{profile.username}
            </Typography>
            {!!profile.affiliations?.length && (
              <Typography variant="body2">
                <em>{profile.affiliations.join(", ")}</em>
              </Typography>
            )}
          </Box>
          {currentUser &&
            !currentUser.is_anonymous &&
            currentUserId !== profile.id &&
            !profile.is_bot && (
              <Button
                primary
                disabled={starting}
                onClick={() =>
                  startDiscussion({ direct: true, user_ids: [profile.id] })
                    .unwrap()
                    .then(({ id: discussionId }) =>
                      navigate(`/discussions?id=${discussionId}`),
                    )
                    .catch(() => {})
                }
                data-testid="sendMessageButton"
                sx={{ alignSelf: "flex-start" }}
              >
                <ChatIcon fontSize="small" sx={{ mr: 0.75 }} />
                Message
              </Button>
            )}
        </Box>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 1, mt: 2 }}>
          {profile.bio && (
            <Typography variant="body2" color="textSecondary">
              {profile.bio}
            </Typography>
          )}
          {profile.contact_email &&
            field(
              "Contact email",
              <Link href={`mailto:${profile.contact_email}`}>
                {profile.contact_email}
              </Link>,
            )}
          {profile.contact_phone &&
            field("Contact phone", profile.contact_phone)}
          {!!profile.roles?.length && field("Roles", chips(profile.roles))}
          {!!profile.groups?.length && field("Groups", chips(profile.groups))}
          {field("Member since", memberSince(profile.created_at))}
        </Box>
        {id && <Activity id={id} />}
      </Paper>
    </>
  );
};

export default withRouter(PublicProfile);
