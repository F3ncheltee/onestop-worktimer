/* Promise wrapper for window.pywebview.api */
(function () {
  let ready = false;
  let readyPromise = null;
  const BROWSER_PREVIEW_TIMEOUT_MS = 15000;

  function apiAvailable() {
    return !!(window.pywebview && window.pywebview.api);
  }

  function whenReady() {
    if (ready) return Promise.resolve();
    if (readyPromise) return readyPromise;
    readyPromise = new Promise((resolve) => {
      if (apiAvailable()) {
        ready = true;
        resolve();
        return;
      }
      window.addEventListener("pywebviewready", () => {
        ready = true;
        resolve();
      });
      // Poll until pywebview injects the bridge (or timeout for browser-only preview).
      const start = Date.now();
      const poll = setInterval(() => {
        if (apiAvailable()) {
          clearInterval(poll);
          ready = true;
          resolve();
        } else if (Date.now() - start > BROWSER_PREVIEW_TIMEOUT_MS) {
          clearInterval(poll);
          resolve();
        }
      }, 100);
    });
    return readyPromise;
  }

  async function call(method, ...args) {
    await whenReady();
    if (!(apiAvailable() && window.pywebview.api[method])) {
      console.warn(`[api] pywebview.api.${method} not available (browser preview mode)`);
      return null;
    }
    try {
      return await window.pywebview.api[method](...args);
    } catch (err) {
      console.error(`[api] ${method} failed`, err);
      throw err;
    }
  }

  window.WT = window.WT || {};
  window.WT.api = new Proxy(
    {},
    {
      get(_target, prop) {
        return (...args) => call(prop, ...args);
      },
    }
  );
  window.WT.apiReady = whenReady;
})();
