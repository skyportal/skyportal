import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Tooltip from "@mui/material/Tooltip";
import { HostChip, brokerHostSummary, hostUrl } from "../broker/BrokerHostChip";
import { useAddHostMutation, useRemoveHostMutation } from "../../ducks/source";
import type { BrokerHost } from "../../ducks/brokers";

const sameName = (a?: string | null, b?: string | null) =>
  !!a &&
  !!b &&
  a.replace(/\s+/g, "").toLowerCase() === b.replace(/\s+/g, "").toLowerCase();

interface SourceHostProps {
  source: any;
  brokerHosts: Record<string, BrokerHost> | null | undefined;
  brokerName?: string | undefined;
  isReadOnly: boolean;
}

const SourceHost = ({
  source,
  brokerHosts,
  brokerName,
  isReadOnly,
}: SourceHostProps) => {
  const [addHost] = useAddHostMutation();
  const [removeHost] = useRemoveHostMutation();

  const host = source.host;
  const brokerHost = brokerHosts?.[source.id];
  const showBrokerHost =
    brokerHost && !sameName(brokerHost.objname, host?.name);
  const nearby: string[] = isReadOnly
    ? []
    : (source.galaxies || []).filter(
        (name: string) => !sameName(name, host?.name),
      );

  if (!host && !brokerHosts && nearby.length === 0) return null;

  return (
    <Box
      sx={{
        flexBasis: "100%",
        display: "flex",
        alignItems: "baseline",
        gap: 1,
      }}
    >
      <b>Host:</b>
      <Box
        sx={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          gap: 1,
        }}
      >
        {host && (
          <HostChip
            host={{
              name: host.name,
              z: host.redshift,
              zErr: host.redshift_error,
              sepArcsec: source.host_offset,
              sepKpc: source.host_distance,
              distMpc: host.distmpc,
              url: hostUrl({ ra: host.ra, dec: host.dec }),
            }}
            onDelete={isReadOnly ? undefined : () => removeHost(source.id)}
          />
        )}
        {showBrokerHost && (
          <HostChip host={brokerHostSummary(brokerHost, brokerName)} />
        )}
        {!host && !brokerHost && (
          <Box component="span" sx={{ color: "text.secondary" }}>
            None
          </Box>
        )}
        {nearby.length > 0 && (
          <Box
            sx={{
              display: "flex",
              flexWrap: "wrap",
              alignItems: "center",
              gap: 0.5,
            }}
          >
            <Box
              component="span"
              sx={{ color: "text.secondary", fontSize: "0.85rem", mr: 0.5 }}
            >
              Nearby
            </Box>
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
          </Box>
        )}
      </Box>
    </Box>
  );
};

export default SourceHost;
