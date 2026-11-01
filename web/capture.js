/* Independent rendered-DOM capture. Executed only in Qt's isolated ApplicationWorld. */
(() => {
  const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
  const unsafeURL = value => /^(javascript|vbscript|file):/i.test(value) || /[?&](?:[^=&#]*(?:token|password|secret|session|api_key)[^=&#]*)=/i.test(value);
  
})();
