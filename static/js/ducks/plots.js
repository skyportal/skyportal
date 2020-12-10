import * as API from "../API";
import store from "../store";

const FETCH_SOURCE_PLOT = "skyportal/FETCH_SOURCE_PLOT";
const FETCH_SOURCE_PLOT_OK = "skyportal/FETCH_SOURCE_PLOT_OK";

// eslint-disable-next-line import/prefer-default-export
export function fetchPlotData(url) {
  return API.GET(url, FETCH_SOURCE_PLOT);
}

const reducer = (state = { plotData: {}, plotIDList: [] }, action) => {
  switch (action.type) {
    case FETCH_SOURCE_PLOT_OK: {
      const plotData = { ...state.plotData };
      const plotIDList = state.plotIDList.slice();

      const { url, ...incomingData } = action.data;
      plotIDList.unshift(url);
      plotData[url] = incomingData;
      if (plotIDList.length >= 40) {
        plotIDList.length = 40;
        Object.keys(plotData).forEach((ID) => {
          if (!plotIDList.includes(ID)) {
            delete plotData[ID];
          }
        });
      }
      return {
        plotData,
        plotIDList,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("plots", reducer);
