import type { ReactNode } from "react";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Tooltip from "@mui/material/Tooltip";
import {
  HostChip,
  brokerHostSummary,
  hostUrl,
  type HostSummary,
} from "../broker/BrokerHostChip";
import FieldLabel from "./FieldLabel";
import { useAddHostMutation, useRemoveHostMutation } from "../../ducks/source";
import type { BrokerHost } from "../../ducks/brokers";

const sameName = (a?: string | null, b?: string | null) =>
  !!a &&
  !!b &&
  a.replace(/\s+/g, "").toLowerCase() === b.replace(/\s+/g, "").toLowerCase();

const formatKpc = (kpc: number) =>
  kpc >= 1000 ? `${(kpc / 1000).toFixed(1)} Mpc` : `${kpc.toFixed(1)} kpc`;

const Group = ({ label, children }: { label: string; children: ReactNode }) => (
  <Box
    sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 0.5 }}
  >
    <Box
      component="span"
      sx={{ color: "text.secondary", fontSize: "0.85rem", mr: 0.25 }}
    >
      {label}
    </Box>
    {children}
  </Box>
);

interface SourceHostProps {
  source: any;
  brokerHosts: Record<string, BrokerHost> | null | undefined;
  brokerName?: string | undefined;
  isReadOnly: boolean;
}

const SourceHost = ({
  source,
  brokerHosts,
  brokerName = "Broker",
  isReadOnly,
}: SourceHostProps) => {
  const [addHost] = useAddHostMutation();
  const [removeHost] = useRemoveHostMutation();

  const host = source.host;
  const brokerHost = brokerHosts?.[source.id];
  const nearby: string[] = isReadOnly
    ? []
    : (source.galaxies || []).filter(
        (name: string) => !sameName(name, host?.name),
      );

  if (!host && !brokerHosts && nearby.length === 0) return null;

  const assigned: HostSummary | null = host && {
    name: host.name,
    heading: "Assigned",
    primary: true,
    z: host.redshift,
    zErr: host.redshift_error,
    sepArcsec: source.host_offset,
    distMpc: host.distmpc,
    url: hostUrl({ ra: host.ra, dec: host.dec }),
    extraRows:
      source.host_distance != null
        ? [["3D separation", formatKpc(source.host_distance)]]
        : [],
  };
  const broker = brokerHost && brokerHostSummary(brokerHost, brokerName);
  const otherBroker =
    assigned && broker && !sameName(broker.name, assigned.name);

  return (
    <Box
      sx={{
        flexBasis: "100%",
        display: "flex",
        alignItems: "baseline",
        gap: 1,
        py: 0.5,
      }}
    >
      <FieldLabel>Host</FieldLabel>
      <Box
        sx={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          columnGap: 2,
          rowGap: 1,
        }}
      >
        {assigned && (
          <HostChip
            host={assigned}
            onDelete={isReadOnly ? undefined : () => removeHost(source.id)}
          />
        )}
        {!assigned && broker && (
          <HostChip host={{ ...broker, primary: true }} />
        )}
        {!assigned && !broker && (
          <Box component="span" sx={{ color: "text.secondary" }}>
            None
          </Box>
        )}
        {otherBroker && (
          <Group label={brokerName}>
            <HostChip
              host={{ ...broker, tag: undefined, heading: brokerName }}
            />
          </Group>
        )}
        {nearby.length > 0 && (
          <Group label="Nearby">
            {nearby.map((name) => (
              <Tooltip key={name} title="Set as host">
                <Chip
                  size="small"
                  variant="outlined"
                  label={name}
                  onClick={() =>
                    addHost({ id: source.id, formData: { galaxyName: name } })
                  }
                  sx={{ borderStyle: "dashed", color: "text.secondary" }}
                />
              </Tooltip>
            ))}
          </Group>
        )}
      </Box>
    </Box>
  );
};

export default SourceHost;
