/* CICS System v14 visual interaction layer for Flask. 
   This file only handles UI behavior; Flask authentication, routes, 
   forms, database calls, and existing application logic remain untouched. */

(function () {
  const sidebar = document.getElementById('cicsSidebar');
  const menu = document.getElementById('menuToggleCics');

  if (menu && sidebar) {
    menu.addEventListener('click', function () {
      sidebar.classList.toggle('open');
    });
  }

  document.querySelectorAll('.sidebar-link').forEach(function (link) {
    link.addEventListener('click', function () {
      if (window.innerWidth <= 860 && sidebar) {
        sidebar.classList.remove('open');
      }
    });
  });

  window.cicsShowToast = function (message) {
    const toast = document.getElementById('cicsToast');
    const text = document.getElementById('cicsToastMsg');

    if (!toast || !text) return;

    text.textContent = message;
    toast.classList.add('show');

    clearTimeout(window.__cicsToastTimer);

    window.__cicsToastTimer = setTimeout(function () {
      toast.classList.remove('show');
    }, 2600);
  };
})();


document.addEventListener('input', function (event) {

    const field = event.target;

    // ==========================================
    // TEXT INPUTS
    // Capitalize the first letter of every word
    // ==========================================
    if (
        field.tagName === 'INPUT' &&
        (field.type === 'text' || !field.type)
    ) {

        const start = field.selectionStart;
        const end = field.selectionEnd;

        field.value = field.value.replace(
            /(^|[\s-])([a-z])/g,
            function (match, separator, letter) {
                return separator + letter.toUpperCase();
            }
        );

        // Keep common CICS terms correct
        field.value = field.value
            .replace(/\bCics\b/gi, 'CICS')
            .replace(/\bIct\b/gi, 'ICT')
            .replace(/\bIot\b/gi, 'IoT')
            .replace(/\bAi\b/gi, 'AI')
            .replace(/\bIt\b/gi, 'IT')
            .replace(/\bIso\b/gi, 'ISO');

        field.setSelectionRange(start, end);
    }


    // ==========================================
    // TEXTAREA / DESCRIPTION
    // Capitalize the first letter of each sentence
    // ==========================================
    if (field.tagName === 'TEXTAREA') {

        const start = field.selectionStart;
        const end = field.selectionEnd;

        field.value = field.value.replace(
            /(^\s*|[.!?]\s+)([a-z])/g,
            function (match, separator, letter) {
                return separator + letter.toUpperCase();
            }
        );

        // Keep common CICS terms correct
        field.value = field.value
            .replace(/\bCics\b/gi, 'CICS')
            .replace(/\bIct\b/gi, 'ICT')
            .replace(/\bIot\b/gi, 'IoT')
            .replace(/\bAi\b/gi, 'AI')
            .replace(/\bIt\b/gi, 'IT')
            .replace(/\bIso\b/gi, 'ISO');

        field.setSelectionRange(start, end);
    }

});
