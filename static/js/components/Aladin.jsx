import React from 'react';

// Aladin is a component used to display the skymap, see https://aladin.cds.unistra.fr/ for more examples

const Aladin = (props) => {

    console.log('props.data ===',props.data)

    // ManageData is used to display the data (the outlines) given in param
    const ManageData = (aladin,data) => {
        console.log('data data data data data data data data data data ',data)
        // check if the data structure is fine else return nothing
        if(!data || !data.geometry || !data.geometry.type ) return null
        // If the type is Point add Point
        if(data?.geometry?.type=='Point' ){
            if(!data.geometry.coordinates || data.geometry.coordinates.length!=2) return null
            let cat = window.A.catalog({name: 'Points', sourceSize: 15});
            aladin.addCatalog(cat);
            cat.addSources([window.A.marker(data.geometry.coordinates[0], data.geometry.coordinates[1], {
                popupTitle: data?.properties?.name,
                popupDesc: '<p> [' + data.geometry.coordinates[0] + ', ' + data.geometry.coordinates[1] + ' ] </p>'
            })]);
        }
        if(data?.geometry?.type=="MultiLineString" ){
            let overlay = window.A.graphicOverlay({color: '#ee2345', lineWidth: 2});
            aladin.addOverlay(overlay);
            // If the data is of type 'MultiLineString', cross the data and display polyline for each tab
            // The following should normally not be written like this but we have to be clear on the data we should have
            if(data.geometry.coordinates[0].length==2) {
                console.log('hello =>',data.geometry.coordinates )
                overlay.add(window.A.polyline(data.geometry.coordinates));
            }
            // If data contains mutli  MultiLineString do the following :
            else{
                for (let i = 0; i < data.geometry.coordinates.length; i++) {
                    overlay.add(window.A.polyline(data.geometry.coordinates[i]));
                }
            }
        }
    }

    React.useEffect(() => {
        // Set the default parameters of the Aladin skymap
        let aladin = window.A.aladin('#aladin-lite-div', {survey: 'P/DSS2/color', fov: 60})
        aladin.setFov(props.fov)
        aladin.gotoRaDec(props.ra, props.dec)

        // check if data exists then go through it and use the ManageData function
        if (props.data && props.data.features && props.data.features.length) {
            props.data.features.map((value, index) => {
                    return (ManageData(aladin, value))
                }
            )
        }

        // check if we got data sources, if yes we display them with the same function as above because of the same data structure
        if(props.sources && props.sources.length>0) {
            props.sources.map((value, index) => {
                    return (ManageData(aladin, value))
                }
            )
        }
    },[props.data])

    // Return the default skymap
    return (
        <div style={{width:'100%',alignItems: 'center',justifyContent: 'center'}}>
            <div id='aladin-lite-div' className="aladin" style={{height:props.height,width:props.width}}/>
        </div>
        )
    }

export default Aladin