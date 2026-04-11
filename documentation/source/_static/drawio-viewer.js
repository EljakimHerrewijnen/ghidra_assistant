(function () {
  const viewerUrl = 'https://embed.diagrams.net/?embed=1&proto=json&spin=1&ui=min&libraries=0&saveAndExit=0&noSaveBtn=1&noExitBtn=1';

  function setError(container, message) {
    container.innerHTML = '<div class="drawio-viewer__error">' + message + '</div>';
  }

  function initializeViewer(container) {
    const iframe = container.querySelector('.drawio-viewer__frame');
    const loading = container.querySelector('.drawio-viewer__loading');
    const src = container.dataset.drawioSrc;
    const height = container.dataset.drawioHeight || '420px';
    const drawioUrl = new URL(src, document.baseURI).toString();

    iframe.style.height = height;
    container.style.minHeight = height;

    const handleMessage = async (event) => {
      if (event.source !== iframe.contentWindow) {
        return;
      }

      let message = event.data;
      if (typeof message === 'string') {
        try {
          message = JSON.parse(message);
        } catch (error) {
          return;
        }
      }

      if (!message || typeof message !== 'object') {
        return;
      }

      if (message.event === 'init') {
        try {
          const response = await fetch(drawioUrl);
          if (!response.ok) {
            throw new Error('HTTP ' + response.status);
          }

          const xml = await response.text();
          iframe.contentWindow.postMessage(
            JSON.stringify({
              action: 'load',
              xml: xml,
              autosave: 0,
              modified: '0',
              saveAndExit: 0,
              noSaveBtn: 1,
              noExitBtn: 1,
              border: 8,
            }),
            '*'
          );
        } catch (error) {
          window.removeEventListener('message', handleMessage);
          setError(container, 'Unable to load the DrawIO diagram.');
        }
      }

      if (message.event === 'load') {
        if (loading) {
          loading.remove();
        }
      }
    };

    window.addEventListener('message', handleMessage);
    iframe.src = viewerUrl;
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.drawio-viewer').forEach(initializeViewer);
  });
})();