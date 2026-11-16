const testingModeText = (service: any) =>
  [
    service.enable_sharing_with_tns && "TNS: payload stored, not sent",
    service.enable_sharing_with_hermes && "Hermes: sent to the test topic",
    service.enable_sharing_with_trove && "TROVE: sent to the test endpoint",
    service.enable_sharing_with_mpc && "MPC: sent to the test endpoint",
  ].filter(Boolean) as string[];

export default testingModeText;
