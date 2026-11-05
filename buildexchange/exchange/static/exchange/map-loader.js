window.mapReady=import('/static/exchange/vendor/maplibre/maplibre-gl.mjs').then(module=>{
    module.setWorkerUrl('/static/exchange/vendor/maplibre/maplibre-gl-worker.mjs');
    window.maplibregl=module;
    return module;
}).catch(error=>{console.warn('Map renderer unavailable:',error.message);return null;});
