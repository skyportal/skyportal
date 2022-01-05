import React from 'react';

// Aladin is a component used to display the skymap, see https://aladin.cds.unistra.fr/ for more examples

const Aladin = (props) => {

    console.log('props.data ===',props.data)

    // ManageData is used to display the data given in param
    const ManageData = (aladin,data) => {
        // check if the data structure is fine else return nothing
        if(!data || !data.geometry || !data.geometry.type ) return null
        // If the type is Point add Point
        if(data?.geometry?.type=='Point'){
            if(!data.geometry.coordinates || data.geometry.coordinates.length!=2) return null
            let cat = window.A.catalog({name: 'Points', sourceSize: 15});
            aladin.addCatalog(cat);
            cat.addSources([window.A.marker(data.geometry.coordinates[0], data.geometry.coordinates[1])]);
        }
        if(data?.geometry?.type=="MultiLineString"){
            let overlay = window.A.graphicOverlay({color: '#ee2345', lineWidth: 2});
            aladin.addOverlay(overlay);
            // If the data is of type 'MultiLineString', cross the data and display polyline for each tab
            for(let i=0;i<data.geometry.coordinates.length;i++){
                console.log()
                overlay.add(window.A.polyline( data.geometry.coordinates[i] ));
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
    },[])

    // Return the default skymap
    return (
        <div style={{width:'100%',alignItems: 'center',justifyContent: 'center'}}>
            <div id='aladin-lite-div' className="aladin" style={{height:props.height,width:props.width}}/>
        </div>
        )
    }

export default Aladin