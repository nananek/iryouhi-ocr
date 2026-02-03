// Streamlit Component Library
const Streamlit = {
    RENDER_EVENT: "streamlit:render",
    events: new EventTarget(),
    
    setComponentReady: function() {
        window.parent.postMessage({
            isStreamlitMessage: true,
            apiVersion: 1,
            type: "streamlit:componentReady"
        }, "*");
    },
    
    setFrameHeight: function(height) {
        const h = height || document.body.scrollHeight;
        window.parent.postMessage({
            isStreamlitMessage: true,
            apiVersion: 1,
            type: "streamlit:setFrameHeight",
            height: h
        }, "*");
    },
    
    setComponentValue: function(value) {
        window.parent.postMessage({
            isStreamlitMessage: true,
            apiVersion: 1,
            type: "streamlit:setComponentValue",
            value: value
        }, "*");
    }
};

window.addEventListener("message", (event) => {
    if (event.data.type === "streamlit:render") {
        const renderEvent = new CustomEvent(Streamlit.RENDER_EVENT, {
            detail: event.data
        });
        Streamlit.events.dispatchEvent(renderEvent);
    }
});
