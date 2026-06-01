// latex_line_numbers.js
// Ensures line numbers are always shown and textarea is always editable

function updateLatexLineNumbers() {
  const textarea = document.getElementById('resumeTextarea');
  const gutter = document.getElementById('latexLineNumbers');
  if (!textarea || !gutter) return;
  const lines = textarea.value.split('\n').length;
  let html = '';
  for (let i = 1; i <= lines; i++) {
    html += `<div class="lx-ln">${i}</div>`;
  }
  gutter.innerHTML = html;
  gutter.scrollTop = textarea.scrollTop;
}

document.addEventListener('DOMContentLoaded', () => {
  const textarea = document.getElementById('resumeTextarea');
  if (textarea) {
    textarea.addEventListener('input', updateLatexLineNumbers);
    textarea.addEventListener('scroll', updateLatexLineNumbers);
    updateLatexLineNumbers();
  }
});

// Patch selectResume to update line numbers after loading a resume
if (window.selectResume) {
  const origSelectResume = window.selectResume;
  window.selectResume = function(id) {
    origSelectResume(id);
    updateLatexLineNumbers();
  };
}
