document.addEventListener('DOMContentLoaded', () => {
  const textArea = document.getElementById('job_text');
  if (textArea) {
    const counter = document.getElementById('char-count');
    const sampleButton = document.getElementById('sample-button');
    const form = document.getElementById('predict-form');

    const updateCount = () => {
      if (counter) counter.textContent = `${textArea.value.length.toLocaleString()} / 10,000`;
    };
    textArea.addEventListener('input', updateCount);
    updateCount();

    sampleButton?.addEventListener('click', () => {
      textArea.value = 'Your online assessment is scheduled for 28 October 2026. The technical interview will take place in 3 days. Your HR interview is next week.';
      updateCount();
      textArea.focus();
    });

    form?.addEventListener('submit', event => {
      if (!textArea.value.trim()) {
        event.preventDefault();
        let alert = form.querySelector('.client-error');
        if (!alert) {
          alert = document.createElement('p');
          alert.className = 'alert error client-error';
          alert.setAttribute('role', 'alert');
          alert.innerHTML = '<span class="alert-icon">!</span><span>Please paste an interview email or hiring update first.</span>';
          form.prepend(alert);
        }
        textArea.focus();
        return;
      }
      const button = form.querySelector('button[type="submit"]');
      if (button) {
        button.disabled = true;
        button.querySelector('span:first-child').textContent = 'Finding dated stages...';
      }
    });
  }

  const eventList = document.getElementById('event-list');
  if (eventList) {
    const count = document.querySelector('.result-count strong');
    const countLabel = document.querySelector('.result-count span');
    const exportButton = document.querySelector('#calendar-form button[type="submit"]');
    const updateEventCount = () => {
      const remaining = eventList.querySelectorAll('.event-card').length;
      if (count) count.textContent = remaining;
      if (countLabel) countLabel.textContent = `dated stage${remaining === 1 ? '' : 's'} found`;
      if (exportButton) exportButton.disabled = remaining === 0;
    };
    eventList.querySelectorAll('.remove').forEach(button => {
      button.addEventListener('click', () => {
        button.closest('.event-card')?.remove();
        updateEventCount();
      });
    });
    updateEventCount();

    document.getElementById('calendar-form')?.addEventListener('submit', () => {
      if (exportButton) {
        exportButton.disabled = true;
        exportButton.querySelector('span:first-child').textContent = 'Connecting to Google Calendar...';
      }
    });
  }

  document.querySelectorAll('.application-toggle').forEach(form => {
    const checkbox = form.querySelector('.application-checkbox');
    const hidden = form.querySelector('input[name="enabled"]');
    const label = form.querySelector('.toggle-label');
    checkbox?.addEventListener('change', () => {
      const wasActive = form.dataset.active === 'true';
      if (wasActive && !checkbox.checked) {
        const confirmed = window.confirm(`Remove all tracked interview rounds for ${form.dataset.label} from Google Calendar?`);
        if (!confirmed) {
          checkbox.checked = true;
          return;
        }
      }
      if (hidden) hidden.value = checkbox.checked ? 'true' : 'false';
      if (label) label.textContent = checkbox.checked ? 'On calendar' : 'Removing...';
      checkbox.disabled = true;
      form.submit();
    });
  });
});
