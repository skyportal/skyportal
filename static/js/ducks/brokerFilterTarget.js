// The broker filter builder targets one broker at a time. The /brokers page
// sets the active broker id here (on mount) so the filter ducks can build
// `/api/brokers/{id}/...` URLs without threading the id through every one of the
// builder's component call sites.
let brokerId = null;

export const setBrokerFilterTarget = (id) => {
  brokerId = id;
};

export const brokerFilterBase = () => `/api/brokers/${brokerId}`;
