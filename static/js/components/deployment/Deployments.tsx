import { Fragment, ReactNode, useState } from "react";
import { Link as RouterLink, useSearchParams } from "react-router-dom";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import utc from "dayjs/plugin/utc";
import { alpha } from "@mui/material/styles";
import Box from "@mui/material/Box";
import Chip, { ChipProps } from "@mui/material/Chip";
import Collapse from "@mui/material/Collapse";
import Divider from "@mui/material/Divider";
import Grid from "@mui/material/Grid";
import Link from "@mui/material/Link";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Tooltip from "@mui/material/Tooltip";
import Typography, { TypographyProps } from "@mui/material/Typography";
import Timeline from "@mui/lab/Timeline";
import TimelineConnector from "@mui/lab/TimelineConnector";
import TimelineContent from "@mui/lab/TimelineContent";
import TimelineDot from "@mui/lab/TimelineDot";
import TimelineItem from "@mui/lab/TimelineItem";
import TimelineOppositeContent, {
  timelineOppositeContentClasses,
} from "@mui/lab/TimelineOppositeContent";
import TimelineSeparator from "@mui/lab/TimelineSeparator";

import RocketLaunchIcon from "@mui/icons-material/RocketLaunchOutlined";
import CommitIcon from "@mui/icons-material/Commit";
import CallMergeIcon from "@mui/icons-material/CallMerge";
import UndoIcon from "@mui/icons-material/Undo";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import LockIcon from "@mui/icons-material/LockOutlined";
import DnsIcon from "@mui/icons-material/DnsOutlined";
import StorageIcon from "@mui/icons-material/StorageOutlined";
import Inventory2Icon from "@mui/icons-material/Inventory2Outlined";
import MemoryIcon from "@mui/icons-material/MemoryOutlined";
import NotificationsActiveIcon from "@mui/icons-material/NotificationsActiveOutlined";
import FeedbackIcon from "@mui/icons-material/FeedbackOutlined";
import CheckCircleIcon from "@mui/icons-material/CheckCircleOutlineOutlined";
import ErrorIcon from "@mui/icons-material/ErrorOutlineOutlined";
import PauseCircleIcon from "@mui/icons-material/PauseCircleOutlineOutlined";
import HourglassIcon from "@mui/icons-material/HourglassEmptyOutlined";
import BlockIcon from "@mui/icons-material/BlockOutlined";
import SettingsIcon from "@mui/icons-material/SettingsOutlined";
import HelpIcon from "@mui/icons-material/HelpOutlineOutlined";

import Spinner from "../Spinner";
import {
  useGetDeploymentsQuery,
  type Deployment,
  type GitLogEntry,
  type InstanceSystem,
} from "../../ducks/deployments";
import { useGetFeedbackQuery } from "../../ducks/feedback";
import FeedbackTab from "./Feedback";
import NotificationToggle from "./NotificationToggle";

dayjs.extend(relativeTime);
dayjs.extend(utc);

type ServiceResponse = NonNullable<InstanceSystem["services"]>[number];
type Process = NonNullable<ServiceResponse["processes"]>[number];
type Service = Omit<ServiceResponse, "processes"> & { processes: Process[] };

const ON_DESKTOP = { display: { xs: "none", md: "block" } };
const EXTERNAL = { target: "_blank", rel: "noreferrer" };

const utcDate = (value?: string | null) => (value ? dayjs.utc(value) : null);

const formatDate = (value?: string | null) =>
  utcDate(value)?.local().format("MMM D, YYYY HH:mm") ?? "";

const formatBytes = (bytes?: number | null) => {
  if (bytes === null || bytes === undefined) return "unknown";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value.toFixed(value >= 10 || unit === 0 ? 0 : 1)} ${units[unit]}`;
};

const Caption = (props: TypographyProps) => (
  <Typography
    variant="caption"
    color="text.secondary"
    component="div"
    {...props}
  />
);

const StateChip = (props: ChipProps) => (
  <Chip size="small" variant="outlined" {...props} />
);

const SubTitle = ({
  icon,
  children,
}: {
  icon: ReactNode;
  children: string;
}) => (
  <Stack direction="row" spacing={1} sx={{ alignItems: "center", mb: 1 }}>
    {icon}
    <Typography sx={{ fontWeight: 600 }}>{children}</Typography>
  </Stack>
);

const StatTile = ({
  label,
  value,
  detail,
}: {
  label: string;
  value: ReactNode;
  detail?: string;
}) => (
  <Box
    sx={{
      p: 2,
      borderRadius: 2,
      height: "100%",
      bgcolor: (theme) =>
        alpha(
          theme.palette.primary.main,
          theme.palette.mode === "dark" ? 0.12 : 0.05,
        ),
    }}
  >
    <Typography variant="body2" color="text.secondary">
      {label}
    </Typography>
    <Tooltip title={detail ?? ""} placement="bottom-start">
      <Typography variant="h5" sx={{ fontWeight: 600, mt: 0.5 }} noWrap>
        {value}
      </Typography>
    </Tooltip>
  </Box>
);

const CommitChips = ({ commit }: { commit?: GitLogEntry | null }) => {
  if (!commit?.sha) return null;
  const link = {
    size: "small",
    variant: "outlined",
    component: "a",
    clickable: true,
    ...EXTERNAL,
  } as const;
  return (
    <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", rowGap: 1 }}>
      <Chip
        {...link}
        icon={<CommitIcon />}
        label={commit.sha.slice(0, 7)}
        href={commit.commit_url ?? undefined}
        sx={{ fontFamily: "monospace" }}
      />
      {commit.pr_nr && (
        <Chip
          {...link}
          icon={<CallMergeIcon />}
          label={`#${commit.pr_nr}`}
          href={commit.pr_url ?? undefined}
        />
      )}
    </Stack>
  );
};

const ChangeList = ({ changes }: { changes: GitLogEntry[] }) => (
  <Box
    component="ul"
    sx={{
      listStyle: "none",
      p: 0,
      m: 0,
      mt: 1,
      maxHeight: "20rem",
      overflow: "auto",
    }}
  >
    {changes.map((change) => (
      <Box
        component="li"
        key={change.sha}
        sx={{ display: "flex", gap: 1, py: 0.5, alignItems: "baseline" }}
      >
        <Link
          {...EXTERNAL}
          href={change.commit_url ?? undefined}
          sx={{ fontFamily: "monospace", fontSize: "0.8rem", flexShrink: 0 }}
        >
          {change.sha?.slice(0, 7)}
        </Link>
        <Typography variant="body2" sx={{ flexGrow: 1 }}>
          {change.description}{" "}
          {change.pr_nr && (
            <Link {...EXTERNAL} href={change.pr_url ?? undefined}>
              {`#${change.pr_nr}`}
            </Link>
          )}
        </Typography>
        <Caption sx={{ flexShrink: 0, display: { xs: "none", sm: "block" } }}>
          {change.time && dayjs(change.time).format("MMM D")}
        </Caption>
      </Box>
    ))}
  </Box>
);

const DeploymentItem = ({
  deployment,
  next,
  isCurrent,
  isLast,
}: {
  deployment: Deployment;
  next?: Deployment | undefined;
  isCurrent: boolean;
  isLast: boolean;
}) => {
  const [open, setOpen] = useState(isCurrent);
  const start = utcDate(deployment.created_at);
  const end = utcDate(next?.created_at);
  const { changes, rollback } = deployment;
  const nChanges = deployment.n_changes ?? 0;

  return (
    <TimelineItem>
      <TimelineOppositeContent sx={{ pt: 1.5 }}>
        <Typography variant="body2" sx={{ fontWeight: 500 }}>
          {start?.local().format("MMM D, YYYY")}
        </Typography>
        <Caption component="span">{start?.local().format("HH:mm")}</Caption>
      </TimelineOppositeContent>
      <TimelineSeparator>
        <TimelineDot
          color={isCurrent ? "primary" : rollback ? "warning" : "grey"}
          variant={isCurrent ? "filled" : "outlined"}
        >
          {rollback ? (
            <UndoIcon fontSize="small" />
          ) : (
            <RocketLaunchIcon fontSize="small" />
          )}
        </TimelineDot>
        {!isLast && <TimelineConnector />}
      </TimelineSeparator>
      <TimelineContent sx={{ pb: 3 }}>
        <Stack
          direction="row"
          spacing={1}
          sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 1 }}
        >
          <Typography sx={{ fontWeight: 600, fontFamily: "monospace" }}>
            v{deployment.version}
          </Typography>
          {isCurrent && <Chip label="Current" color="primary" size="small" />}
          {rollback && (
            <StateChip icon={<UndoIcon />} label="Rollback" color="warning" />
          )}
          <CommitChips commit={deployment.commit} />
        </Stack>
        {deployment.commit?.description && (
          <Typography variant="body2" sx={{ mt: 1 }}>
            {deployment.commit.description}
          </Typography>
        )}
        <Caption>
          {end
            ? `Live for ${end.from(start, true)}`
            : `Live since ${start?.fromNow(true)}`}
        </Caption>
        {!changes ? (
          !isLast && (
            <Caption>
              Changes unavailable: a commit is missing from the running history
            </Caption>
          )
        ) : nChanges > 0 ? (
          <>
            <Link
              component="button"
              variant="body2"
              onClick={() => setOpen(!open)}
              sx={{ display: "inline-flex", alignItems: "center", mt: 0.5 }}
            >
              {nChanges} new commit{nChanges > 1 ? "s" : ""}
              {open ? (
                <ExpandLessIcon fontSize="small" />
              ) : (
                <ExpandMoreIcon fontSize="small" />
              )}
            </Link>
            <Collapse in={open}>
              <ChangeList changes={changes} />
              {nChanges > changes.length && (
                <Caption>and {nChanges - changes.length} more</Caption>
              )}
            </Collapse>
          </>
        ) : (
          !rollback && <Caption>Same code, redeployed</Caption>
        )}
      </TimelineContent>
    </TimelineItem>
  );
};

const processState = (state: string) => {
  if (state === "RUNNING")
    return { color: "success" as const, icon: <CheckCircleIcon /> };
  if (["STARTING", "BACKOFF", "STOPPING"].includes(state))
    return { color: "warning" as const, icon: <HourglassIcon /> };
  if (["FATAL", "UNKNOWN"].includes(state))
    return { color: "error" as const, icon: <ErrorIcon /> };
  return { color: "default" as const, icon: <PauseCircleIcon /> };
};

const Facts = ({ facts }: { facts: [string, ReactNode][] }) => (
  <Box
    component="dl"
    sx={{
      display: "grid",
      gridTemplateColumns: "max-content 1fr",
      columnGap: 2,
      rowGap: 1,
      m: 0,
      "& dt": { color: "text.secondary" },
      "& dd": { m: 0, fontFamily: "monospace", wordBreak: "break-all" },
    }}
  >
    {facts.map(([label, value]) => (
      <Fragment key={label}>
        <Typography component="dt" variant="body2">
          {label}
        </Typography>
        <Typography component="dd" variant="body2">
          {value ?? "unknown"}
        </Typography>
      </Fragment>
    ))}
  </Box>
);

const Meter = ({
  label,
  value,
  total,
  detail,
}: {
  label: string;
  value: number;
  total?: number | null;
  detail: string;
}) => {
  const ratio = total ? value / total : 0;
  const color = ratio >= 0.9 ? "error" : ratio >= 0.75 ? "warning" : "primary";
  return (
    <>
      <Stack
        direction="row"
        sx={{ justifyContent: "space-between", mb: 0.5, gap: 1 }}
      >
        <Typography variant="body2" color="text.secondary">
          {label}
        </Typography>
        <Typography variant="body2" sx={{ fontWeight: 600 }}>
          {detail}
        </Typography>
      </Stack>
      <Box
        sx={{
          height: 8,
          borderRadius: 4,
          overflow: "hidden",
          bgcolor: (theme) => alpha(theme.palette[color].main, 0.15),
        }}
      >
        <Box
          sx={{
            width: `${Math.min(100, ratio * 100)}%`,
            height: "100%",
            borderRadius: 4,
            bgcolor: `${color}.main`,
          }}
        />
      </Box>
    </>
  );
};

const Resources = ({
  resources,
}: {
  resources: NonNullable<InstanceSystem["resources"]>;
}) => {
  const memoryUsed =
    (resources.memory_total ?? 0) - (resources.memory_available ?? 0);
  const diskUsed = (resources.disk_total ?? 0) - (resources.disk_free ?? 0);
  const load = resources.load_average?.[0] ?? 0;
  const meters = [
    {
      label: "Host memory",
      value: memoryUsed,
      total: resources.memory_total,
      detail: `${formatBytes(memoryUsed)} of ${formatBytes(resources.memory_total)}`,
    },
    {
      label: "Host CPU load (1 min)",
      value: load,
      total: resources.cpu_count,
      detail: `${resources.load_average?.[0]?.toFixed(2) ?? "unknown"} on ${resources.cpu_count ?? "?"} CPUs`,
    },
    {
      label: "Disk",
      value: diskUsed,
      total: resources.disk_total,
      detail: `${formatBytes(diskUsed)} of ${formatBytes(resources.disk_total)}`,
    },
  ];
  return (
    <Grid container spacing={3}>
      {meters.map((meter) => (
        <Grid key={meter.label} size={{ xs: 12, md: 4 }}>
          <Meter {...meter} />
        </Grid>
      ))}
    </Grid>
  );
};

const INACTIVE = {
  disabled: {
    label: "disabled",
    icon: <BlockIcon />,
    help: "Listed in services.disabled in the config",
  },
  not_configured: {
    label: "not configured",
    icon: <SettingsIcon />,
    help: "Enabled, but the config does not provide what it needs, so supervisor does not run it",
  },
  unknown: {
    label: "unknown",
    icon: <HelpIcon />,
    help: "Supervisor is not reachable",
  },
};

const serviceSummary = ({
  status,
  processes,
}: Service): ChipProps & { muted: boolean; help?: string } => {
  const inactive =
    status !== "enabled"
      ? INACTIVE[status]
      : processes.length === 0 && INACTIVE.unknown;
  if (inactive) return { ...inactive, color: "default" as const, muted: true };
  const running = processes.filter((p) => p.state === "RUNNING").length;
  if (!running) {
    const { state } = processes[0]!;
    return { label: state.toLowerCase(), ...processState(state), muted: false };
  }
  const count = processes.length > 1 ? ` ${running}/${processes.length}` : "";
  return {
    label: `running${count}`,
    ...processState(running === processes.length ? "RUNNING" : "STARTING"),
    muted: false,
  };
};

const RANK: Record<string, number> = { not_configured: 1, disabled: 2 };

const serviceRank = (service: Service) =>
  service.processes.length > 0 ? 0 : (RANK[service.status] ?? 3);

const serviceMemory = (service: Service) =>
  service.processes.reduce((sum, p) => sum + (p.memory ?? 0), 0);

const MemoryBar = ({
  memory,
  largest,
  title,
}: {
  memory: number;
  largest: number;
  title: string;
}) => (
  <Tooltip title={memory ? title : ""} placement="top">
    <Box sx={{ ...ON_DESKTOP, py: 1 }}>
      <Box
        sx={{
          width: `${Math.min(100, Math.max((memory / largest) * 100, memory ? 1 : 0))}%`,
          height: 8,
          borderRadius: "0 4px 4px 0",
          bgcolor: "primary.main",
        }}
      />
    </Box>
  </Tooltip>
);

const Uptime = ({ since }: { since?: string | null | undefined }) => {
  const date = utcDate(since);
  return (
    <Tooltip title={date ? `Since ${formatDate(since)}` : ""}>
      <Typography variant="body2" color="text.secondary" sx={ON_DESKTOP} noWrap>
        {date?.fromNow(true)}
      </Typography>
    </Tooltip>
  );
};

const Services = ({
  services,
  supervisorAvailable,
}: {
  services: Service[];
  supervisorAvailable: boolean;
}) => {
  const [expanded, setExpanded] = useState<string[]>([]);
  const isOpen = (service: Service) =>
    service.processes.length > 1 && expanded.includes(service.name);
  const toggle = (name: string) =>
    setExpanded(
      expanded.includes(name)
        ? expanded.filter((other) => other !== name)
        : [...expanded, name],
    );
  const sorted = [...services].sort(
    (a, b) =>
      serviceRank(a) - serviceRank(b) ||
      serviceMemory(b) - serviceMemory(a) ||
      a.name.localeCompare(b.name),
  );
  const largest = Math.max(
    1,
    ...services.flatMap((service) =>
      isOpen(service)
        ? service.processes.map((p) => p.memory ?? 0)
        : [serviceMemory(service)],
    ),
  );
  const active = services.filter((s) => s.processes.length > 0);
  const running = active.filter((s) =>
    s.processes.some((p) => p.state === "RUNNING"),
  ).length;
  const count = (status: string) =>
    services.filter((s) => s.status === status).length;
  const total = services.reduce((sum, s) => sum + serviceMemory(s), 0);

  return (
    <>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
        {running} running, {active.length - running} stopped,{" "}
        {count("not_configured")} not configured, {count("disabled")} disabled.{" "}
        {supervisorAvailable
          ? `${formatBytes(total)} of resident memory in total.`
          : "Supervisor is not reachable, so process states are unknown."}
      </Typography>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "minmax(0, 1fr) auto auto",
            md: "minmax(12rem, 16rem) 9rem minmax(0, 1fr) 5rem 7rem",
          },
          columnGap: 2,
          rowGap: 0.5,
          alignItems: "center",
        }}
      >
        {["Service", "State", "Memory", "", "Up for"].map((header, index) => (
          <Caption
            key={index}
            sx={index === 2 || index === 4 ? ON_DESKTOP : {}}
          >
            {header}
          </Caption>
        ))}
        {sorted.map((service) => {
          const { muted, help = "", ...summary } = serviceSummary(service);
          const memory = serviceMemory(service);
          const multiple = service.processes.length > 1;
          const open = isOpen(service);
          const started = service.processes
            .filter((p) => p.state === "RUNNING" && p.started_at)
            .map((p) => p.started_at!)
            .sort()[0];
          return (
            <Fragment key={service.name}>
              <Stack
                direction="row"
                sx={{
                  alignItems: "center",
                  minWidth: 0,
                  opacity: muted ? 0.6 : 1,
                  cursor: multiple ? "pointer" : "default",
                }}
                onClick={() => multiple && toggle(service.name)}
              >
                {multiple &&
                  (open ? (
                    <ExpandLessIcon fontSize="small" />
                  ) : (
                    <ExpandMoreIcon fontSize="small" />
                  ))}
                <Typography
                  variant="body2"
                  sx={{ fontFamily: "monospace" }}
                  noWrap
                >
                  {service.name}
                </Typography>
              </Stack>
              <Tooltip title={help}>
                <Box sx={{ opacity: muted ? 0.7 : 1 }}>
                  <StateChip {...summary} />
                </Box>
              </Tooltip>
              <MemoryBar
                memory={open ? 0 : memory}
                largest={largest}
                title={`${service.name}: ${formatBytes(memory)}`}
              />
              <Typography variant="body2" sx={{ textAlign: "right" }}>
                {memory > 0 && formatBytes(memory)}
              </Typography>
              <Uptime since={started} />
              {open &&
                service.processes.map((process) => (
                  <Fragment key={process.name}>
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      sx={{ fontFamily: "monospace", pl: 3 }}
                      noWrap
                    >
                      {process.name}
                    </Typography>
                    <Box>
                      <StateChip
                        label={process.state.toLowerCase()}
                        {...processState(process.state)}
                      />
                    </Box>
                    <MemoryBar
                      memory={process.memory ?? 0}
                      largest={largest}
                      title={`${process.name} (pid ${process.pid}): ${formatBytes(process.memory)}`}
                    />
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      sx={{ textAlign: "right" }}
                    >
                      {!!process.memory && formatBytes(process.memory)}
                    </Typography>
                    <Uptime
                      since={
                        process.state === "RUNNING" ? process.started_at : null
                      }
                    />
                  </Fragment>
                ))}
            </Fragment>
          );
        })}
      </Box>
    </>
  );
};

const InstanceDetails = ({ system }: { system: InstanceSystem }) => (
  <Grid container spacing={3}>
    {system.resources && (
      <Grid size={12}>
        <Resources resources={system.resources} />
      </Grid>
    )}
    <Grid size={{ xs: 12, md: 6 }}>
      <SubTitle icon={<DnsIcon fontSize="small" color="action" />}>
        Host
      </SubTitle>
      <Facts
        facts={[
          ["Hostname", system.hostname],
          ["Platform", system.platform],
          ["Python", system.python_version],
        ]}
      />
    </Grid>
    <Grid size={{ xs: 12, md: 6 }}>
      <SubTitle icon={<StorageIcon fontSize="small" color="action" />}>
        Database
      </SubTitle>
      <Facts
        facts={[
          ["Name", system.database_name],
          ["PostgreSQL", system.postgres_version],
          ["Size", system.database_size],
          ["Migration", system.migration],
        ]}
      />
    </Grid>
    <Grid size={12}>
      <SubTitle icon={<Inventory2Icon fontSize="small" color="action" />}>
        Packages
      </SubTitle>
      <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", rowGap: 1 }}>
        {Object.entries(system.packages ?? {}).map(([name, version]) => (
          <Chip
            key={name}
            label={`${name} ${version}`}
            size="small"
            sx={{ fontFamily: "monospace" }}
          />
        ))}
      </Stack>
    </Grid>
    <Grid size={12}>
      <SubTitle icon={<MemoryIcon fontSize="small" color="action" />}>
        Services
      </SubTitle>
      <Services
        services={(system.services ?? []).map((service) => ({
          ...service,
          processes: service.processes ?? [],
        }))}
        supervisorAvailable={system.supervisor_available ?? false}
      />
    </Grid>
  </Grid>
);

const Deployments = () => {
  const { data, isLoading, isError } = useGetDeploymentsQuery();
  const { data: feedback = [] } = useGetFeedbackQuery();
  const [searchParams, setSearchParams] = useSearchParams();

  if (isLoading) return <Spinner />;
  if (isError || !data)
    return <Typography>Could not load the deployment information.</Typography>;

  const isAdmin = Boolean(data.system);
  const tabs = ["history", "feedback", "notifications"];
  if (isAdmin) tabs.push("instance");
  const requested = searchParams.get("tab") ?? "";
  const tab = tabs.includes(requested) ? requested : "history";
  const openFeedback = feedback.filter((message) => !message.resolved).length;
  const deployments = data.deployments ?? [];
  const deployedAt = utcDate(data.deployed_at);
  const startedAt = utcDate(data.started_at);
  const hasPrevious = deployments.length > 1;
  const tiles = [
    {
      label: "Deployed",
      value: deployedAt?.fromNow() ?? "unknown",
      detail: formatDate(data.deployed_at),
    },
    {
      label: "Up for",
      value: startedAt?.fromNow(true) ?? "unknown",
      detail: `Since ${formatDate(data.started_at)}`,
    },
    {
      label: "Deployments in the last 30 days",
      value: deployments.filter((deployment) =>
        utcDate(deployment.created_at)?.isAfter(dayjs().subtract(30, "day")),
      ).length,
    },
    {
      label: "Commits in this deployment",
      value: hasPrevious ? (deployments[0]?.n_changes ?? "unknown") : "First",
      detail: hasPrevious
        ? "Commits since the previous deployment"
        : "No earlier deployment to compare with",
    },
  ];

  return (
    <Stack spacing={2}>
      <Paper
        variant="outlined"
        sx={{
          p: { xs: 2, md: 3 },
          borderRadius: 2,
          background: (theme) =>
            `linear-gradient(135deg, ${alpha(theme.palette.primary.main, 0.1)}, transparent 60%)`,
        }}
      >
        <Stack spacing={1.5}>
          <Stack direction="row" spacing={1.5} sx={{ alignItems: "center" }}>
            <RocketLaunchIcon color="primary" sx={{ fontSize: "2.5rem" }} />
            <Box>
              <Typography variant="h5" sx={{ fontWeight: 700 }}>
                {data.title}
              </Typography>
              <Typography color="text.secondary">
                Running SkyPortal{" "}
                <Box component="code" sx={{ fontWeight: 600 }}>
                  v{data.version}
                </Box>
              </Typography>
            </Box>
          </Stack>
          {data.commit?.description && (
            <Typography>
              Latest change: <b>{data.commit.description}</b>
            </Typography>
          )}
          <CommitChips commit={data.commit} />
        </Stack>
        <Divider sx={{ my: 2.5 }} />
        <Grid container spacing={2}>
          {tiles.map((tile) => (
            <Grid key={tile.label} size={{ xs: 6, md: 3 }}>
              <StatTile {...tile} />
            </Grid>
          ))}
        </Grid>
      </Paper>

      <Paper variant="outlined" sx={{ borderRadius: 2 }}>
        <Tabs
          value={tab}
          onChange={(_, value) =>
            setSearchParams({ tab: value }, { replace: true })
          }
          variant="scrollable"
          sx={{ px: { xs: 1, md: 2 }, borderBottom: 1, borderColor: "divider" }}
        >
          <Tab
            value="history"
            icon={<RocketLaunchIcon />}
            iconPosition="start"
            label={`Deployment history (${deployments.length})`}
          />
          <Tab
            value="feedback"
            icon={<FeedbackIcon />}
            iconPosition="start"
            label={
              isAdmin && openFeedback
                ? `Feedback (${openFeedback})`
                : "Feedback"
            }
          />
          <Tab
            value="notifications"
            icon={<NotificationsActiveIcon />}
            iconPosition="start"
            label="Notifications"
          />
          {isAdmin && (
            <Tab
              value="instance"
              icon={<DnsIcon />}
              iconPosition="start"
              label={
                <Tooltip title="Only visible to system admins">
                  <Stack
                    direction="row"
                    spacing={0.5}
                    sx={{ alignItems: "center" }}
                  >
                    <span>Instance details</span>
                    <LockIcon fontSize="inherit" />
                  </Stack>
                </Tooltip>
              }
            />
          )}
        </Tabs>
        <Box sx={{ p: { xs: 2, md: 3 } }}>
          {tab === "feedback" ? (
            <FeedbackTab title={data.title} isAdmin={isAdmin} />
          ) : tab === "notifications" ? (
            <NotificationToggle type="deployments">
              Get notified each time a new version is deployed. Delivery by
              email or Slack is set with the settings button, and your contact
              details in your <RouterLink to="/profile">profile</RouterLink>.
            </NotificationToggle>
          ) : tab === "instance" && data.system ? (
            <InstanceDetails system={data.system} />
          ) : deployments.length === 0 ? (
            <Typography color="text.secondary">
              No deployment recorded yet.
            </Typography>
          ) : (
            <Timeline
              sx={{
                p: 0,
                m: 0,
                [`& .${timelineOppositeContentClasses.root}`]: {
                  flex: { xs: 0.35, md: 0.15 },
                },
              }}
            >
              {deployments.map((deployment, index) => (
                <DeploymentItem
                  key={deployment.id}
                  deployment={deployment}
                  next={deployments[index - 1]}
                  isCurrent={index === 0}
                  isLast={index === deployments.length - 1}
                />
              ))}
            </Timeline>
          )}
        </Box>
      </Paper>
    </Stack>
  );
};

export default Deployments;
