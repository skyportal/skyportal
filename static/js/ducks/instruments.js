import * as API from '../API';
import store from '../store';


const FETCH_INSTRUMENTS = 'skyportal/FETCH_INSTRUMENTS';
const FETCH_INSTRUMENTS_OK = 'skyportal/FETCH_INSTRUMENTS_OK';

const FETCH_INSTRUMENT_OBS_PARAMS = 'skyportal/FETCH_INSTRUMENT_OBS_PARAMS';
const FETCH_INSTRUMENT_OBS_PARAMS_OK = 'skyportal/FETCH_INSTRUMENT_OBS_PARAMS_OK';

export const fetchInstruments = () => (
  API.GET('/api/instrument', FETCH_INSTRUMENTS)
);

export const fetchInstrumentObsParams = () => (
  API.GET('/api/internal/instrument_obs_params', FETCH_INSTRUMENT_OBS_PARAMS)
);

const reducer = (state={ instrumentList: [], instrumentObsParams: {} }, action) => {
  switch (action.type) {
    case FETCH_INSTRUMENTS_OK: {
      const instruments = action.data;
      return {
        ...state,
        instrumentList: instruments
      };
    }
    case FETCH_INSTRUMENT_OBS_PARAMS_OK: {
      const instrumentObsParams = action.data;
      return {
        ...state,
        instrumentObsParams
      };
    }
    default:
      return state;
  }
};

store.injectReducer('instruments', reducer);
