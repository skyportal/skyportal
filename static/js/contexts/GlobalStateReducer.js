// Nico Vermaas - 2 jul 2021
// This is the reducer for the global state provider.

// possible actions
export const SET_STATUS_DATA = 'SET_STATUS_DATA'
export const SET_FETCHED_DATA = 'SET_FETCHED_DATA'
export const SET_FETCHED_TCA = 'SET_STATUS_TCA'
export const SET_FETCHED_ZADKO = 'SET_STATUS_ZADKO'


export const ALADIN_RA = 'ALADIN_RA'
export const ALADIN_DEC = 'ALADIN_DEC'
export const ALADIN_FOV = 'ALADIN_FOV'
export const ALADIN_MODE = 'ALADIN_MODE'
export const TCA = 'TCA'
export const ZADKO = 'ZADKO'
export const MOC = 'MOC'
//export const TELESCOPE = 'TELESCOPE'
export const ALADIN_HIGHLIGHT = 'ALADIN_HIGHLIGHT'

export const initialState = {
        status_data : "unfetched",
        fetched_data: undefined,

        aladin_ra: undefined,
        aladin_dec: undefined,
        aladin_fov: "10",
        aladin_mode: "rectangle",
        tca: undefined,
        zadko: undefined,
        moc: undefined,
        aladin_highlight: undefined
}

export const reducer = (state, action) => {
    switch (action.type) {

        case SET_STATUS_DATA:
            return {
                ...state,
                status_data: action.status_data
            };

        case SET_FETCHED_DATA:
            return {
                ...state,
                fetched_data: action.fetched_data
            };

        case SET_FETCHED_TCA:
            return {
                ...state,
                fetched_tca: action.fetched_tca
            };
        
        case SET_FETCHED_ZADKO:
            return {
                ...state,
                fetched_zadko: action.fetched_zadko
            };

        case ALADIN_RA:
            return {
                ...state,
                aladin_ra: action.aladin_ra
            };

        case ALADIN_DEC:
            return {
                ...state,
                aladin_dec: action.aladin_dec
            };

        case ALADIN_FOV:
            return {
                ...state,
                aladin_fov: action.aladin_fov
            };

        case ALADIN_MODE:

            return {
                ...state,
                aladin_mode: action.aladin_mode
            };
        
        case TCA:

            return {
                ...state,
                tca: action.tca
            };

        case ZADKO:

            return {
                ...state,
                zadko: action.zadko
            };

        case MOC:

            return {
                ...state,
                MOC: action.moc
            };

        case ALADIN_HIGHLIGHT:

            return {
                ...state,
                aladin_highlight: action.aladin_highlight
            };

        default:
            return state;
    }
};