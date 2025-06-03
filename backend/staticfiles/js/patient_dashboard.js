/**
 * Patient Dashboard functionality for Medical Portal
 * Provides appointment management, health tracking, and patient-specific features
 */

document.addEventListener('DOMContentLoaded', function() {
  // Run immediately
  // adjustDashboardHeight(); // Disabled - causing footer overlap

  // Initialize components
  initAppointmentSystem();
  initHealthMetricsCharts();
  initHealthRecordsAccordion();
  setupEventListeners();
  equalizeCardHeights();
  truncateDocumentTitles();


  // Re-equalize card heights and adjust dashboard height when window is resized
  window.addEventListener('resize', debounce(function() {
    // adjustDashboardHeight(); // Disabled - causing footer overlap
    equalizeCardHeights();

  }, 200));

  // Re-run truncation after HTMX swaps content
  document.body.addEventListener('htmx:afterSwap', function(event) {
    truncateDocumentTitles();
  });

  // Also re-run truncation after the page fully loads
  window.addEventListener('load', function() {
    truncateDocumentTitles();
  });

  // And run it again after a delay to catch any late-loading content
  setTimeout(truncateDocumentTitles, 1000);

  /**
   * Initialize the appointment scheduling and management system
   */
  function initAppointmentSystem() {
    const appointmentCalendar = document.getElementById('appointment-calendar');
    if (!appointmentCalendar) return;

    // Check if flatpickr is loaded
    if (typeof flatpickr === 'undefined') {
      console.warn('Flatpickr is not loaded. Calendar initialization skipped.');
      return;
    }

    // Get unavailable dates from data attribute
    const unavailableDates = JSON.parse(appointmentCalendar.dataset.unavailableDates || '[]');

    // Initialize date picker
    const datePicker = flatpickr(appointmentCalendar, {
      inline: true,
      minDate: 'today',
      disable: unavailableDates,
      locale: {
        firstDayOfWeek: 1 // Start with Monday
      },
      onChange: function(selectedDates, dateStr) {
        if (selectedDates.length > 0) {
          // Fetch available time slots for selected date
          fetchAvailableTimeSlots(dateStr);
        }
      }
    });

    // Initialize time slot selection
    const timeSlotContainer = document.getElementById('appointment-time-slots');
    if (timeSlotContainer) {
      timeSlotContainer.addEventListener('click', function(e) {
        const timeSlot = e.target.closest('.time-slot');
        if (timeSlot) {
          // Remove selection from other slots
          document.querySelectorAll('.time-slot.selected').forEach(slot => {
            slot.classList.remove('selected', 'bg-blue-100', 'border-blue-500');
            slot.classList.add('bg-white', 'border-gray-300');
          });

          // Select this slot
          timeSlot.classList.remove('bg-white', 'border-gray-300');
          timeSlot.classList.add('selected', 'bg-blue-100', 'border-blue-500');

          // Update hidden input
          const timeInput = document.getElementById('appointment_time');
          if (timeInput) {
            timeInput.value = timeSlot.dataset.time;
          }

          // Enable submit button
          const submitButton = document.getElementById('schedule-appointment-btn');
          if (submitButton) {
            submitButton.disabled = false;
          }
        }
      });
    }
  }

  /**
   * Fetch available time slots for a selected date
   */
  function fetchAvailableTimeSlots(date) {
    const timeSlotContainer = document.getElementById('appointment-time-slots');
    if (!timeSlotContainer) return;

    // Show loading indicator
    timeSlotContainer.innerHTML = '<div class="text-center py-4"><svg class="animate-spin h-5 w-5 text-blue-500 mx-auto" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg><p class="mt-2 text-sm text-gray-500">Loading available times...</p></div>';

    // Get doctor ID if applicable
    let doctorId = '';
    const doctorSelect = document.getElementById('appointment_doctor');
    if (doctorSelect) {
      doctorId = doctorSelect.value;
    }

    // Get appointment type if applicable
    let appointmentType = '';
    const typeSelect = document.getElementById('appointment_type');
    if (typeSelect) {
      appointmentType = typeSelect.value;
    }

    // Get CSRF token
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

    // Fetch available time slots
    fetch('/api/appointments/available-slots/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify({
        date: date,
        doctor_id: doctorId,
        appointment_type: appointmentType
      })
    })
    .then(response => response.json())
    .then(data => {
      if (data.time_slots && data.time_slots.length > 0) {
        renderTimeSlots(data.time_slots, timeSlotContainer);
      } else {
        timeSlotContainer.innerHTML = '<div class="text-center py-4"><p class="text-gray-500">No available time slots for this date. Please select another date.</p></div>';
      }
    })
    .catch(error => {
      console.error('Error fetching time slots:', error);
      timeSlotContainer.innerHTML = '<div class="text-center py-4"><p class="text-red-500">Error loading time slots. Please try again.</p></div>';
    });
  }

  /**
   * Render time slots in the container
   */
  function renderTimeSlots(timeSlots, container) {
    // Clear previous slots
    container.innerHTML = '';

    // Group slots by morning, afternoon, evening
    const groupedSlots = {
      morning: timeSlots.filter(slot => {
        const hour = parseInt(slot.split(':')[0]);
        return hour >= 7 && hour < 12;
      }),
      afternoon: timeSlots.filter(slot => {
        const hour = parseInt(slot.split(':')[0]);
        return hour >= 12 && hour < 17;
      }),
      evening: timeSlots.filter(slot => {
        const hour = parseInt(slot.split(':')[0]);
        return hour >= 17 && hour < 21;
      })
    };

    // Create time slot groups
    for (const [timeOfDay, slots] of Object.entries(groupedSlots)) {
      if (slots.length === 0) continue;

      const groupTitle = document.createElement('h4');
      groupTitle.className = 'text-sm font-medium text-gray-700 mt-4 mb-2';

      switch (timeOfDay) {
        case 'morning':
          groupTitle.textContent = 'Morning';
          break;
        case 'afternoon':
          groupTitle.textContent = 'Afternoon';
          break;
        case 'evening':
          groupTitle.textContent = 'Evening';
          break;
      }

      container.appendChild(groupTitle);

      const slotsGrid = document.createElement('div');
      slotsGrid.className = 'grid grid-cols-3 sm:grid-cols-4 gap-2';

      slots.forEach(slot => {
        const formattedTime = formatTime(slot);

        const slotButton = document.createElement('div');
        slotButton.className = 'time-slot cursor-pointer py-2 px-3 border border-gray-300 rounded-md text-center text-sm bg-white hover:bg-gray-50';
        slotButton.dataset.time = slot;
        slotButton.textContent = formattedTime;

        slotsGrid.appendChild(slotButton);
      });

      container.appendChild(slotsGrid);
    }
  }

  /**
   * Format time from 24-hour to 12-hour format
   */
  function formatTime(time24h) {
    const [hours, minutes] = time24h.split(':');
    const hour = parseInt(hours);

    return `${hour % 12 || 12}:${minutes} ${hour >= 12 ? 'PM' : 'AM'}`;
  }

  /**
   * Initialize charts for health metrics
   */
  function initHealthMetricsCharts() {
    // Only proceed if Chart.js is loaded
    if (typeof Chart === 'undefined') return;

    // Blood pressure chart
    const bpChartCanvas = document.getElementById('blood-pressure-chart');
    if (bpChartCanvas) {
      const bpChartData = JSON.parse(bpChartCanvas.dataset.chartData || '{}');

      new Chart(bpChartCanvas, {
        type: 'line',
        data: {
          labels: bpChartData.labels || [],
          datasets: [
            {
              label: 'Systolic',
              data: bpChartData.systolic || [],
              borderColor: 'rgba(239, 68, 68, 1)',
              backgroundColor: 'rgba(239, 68, 68, 0.1)',
              tension: 0.2,
              borderWidth: 2,
              pointRadius: 3
            },
            {
              label: 'Diastolic',
              data: bpChartData.diastolic || [],
              borderColor: 'rgba(59, 130, 246, 1)',
              backgroundColor: 'rgba(59, 130, 246, 0.1)',
              tension: 0.2,
              borderWidth: 2,
              pointRadius: 3
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: {
              beginAtZero: false,
              title: {
                display: true,
                text: 'mmHg'
              }
            },
            x: {
              title: {
                display: true,
                text: 'Date'
              }
            }
          },
          plugins: {
            tooltip: {
              mode: 'index',
              intersect: false
            }
          }
        }
      });
    }

    // Weight chart
    const weightChartCanvas = document.getElementById('weight-chart');
    if (weightChartCanvas) {
      const weightChartData = JSON.parse(weightChartCanvas.dataset.chartData || '{}');

      new Chart(weightChartCanvas, {
        type: 'line',
        data: {
          labels: weightChartData.labels || [],
          datasets: [{
            label: 'Weight',
            data: weightChartData.data || [],
            borderColor: 'rgba(16, 185, 129, 1)',
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            tension: 0.3,
            fill: true
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: {
              beginAtZero: false,
              title: {
                display: true,
                text: 'kg'
              }
            }
          }
        }
      });
    }
  }

  /**
   * Initialize accordion functionality for medical records
   */
  function initHealthRecordsAccordion() {
    const accordionItems = document.querySelectorAll('.record-accordion-item');
    accordionItems.forEach(item => {
      const header = item.querySelector('.record-accordion-header');
      const content = item.querySelector('.record-accordion-content');

      header.addEventListener('click', () => {
        // Check if this item is already active
        const isActive = item.classList.contains('active');

        // Close all items
        accordionItems.forEach(otherItem => {
          otherItem.classList.remove('active');
          const otherContent = otherItem.querySelector('.record-accordion-content');
          otherContent.style.maxHeight = null;
        });

        // If the clicked item wasn't active, open it
        if (!isActive) {
          item.classList.add('active');
          content.style.maxHeight = content.scrollHeight + 'px';
        }
      });
    });
  }

  /**
   * Set up event listeners for patient dashboard components
   */
  function setupEventListeners() {
    // Medication reminder toggle
    const reminderToggles = document.querySelectorAll('.medication-reminder-toggle');
    reminderToggles.forEach(toggle => {
      toggle.addEventListener('change', function() {
        const medicationId = this.dataset.medicationId;
        const isEnabled = this.checked;

        updateMedicationReminder(medicationId, isEnabled);
      });
    });

    // Doctor filter for appointment scheduling
    const doctorSelect = document.getElementById('appointment_doctor');
    if (doctorSelect) {
      doctorSelect.addEventListener('change', function() {
        // Reset date selection
        const appointmentCalendar = document.getElementById('appointment-calendar');
        if (appointmentCalendar && typeof appointmentCalendar._flatpickr !== 'undefined') {
          appointmentCalendar._flatpickr.clear();
        }

        // Clear time slots
        const timeSlotContainer = document.getElementById('appointment-time-slots');
        if (timeSlotContainer) {
          timeSlotContainer.innerHTML = '<div class="text-center py-4"><p class="text-gray-500">Please select a date to see available times.</p></div>';
        }

        // Update hidden input
        const doctorInput = document.getElementById('appointment_doctor_id');
        if (doctorInput) {
          doctorInput.value = this.value;
        }

        // Update available dates based on doctor's schedule
        updateAvailableDates(this.value);
      });
    }

    // Health metric form submission
    const healthMetricForm = document.getElementById('health-metric-form');
    if (healthMetricForm) {
      healthMetricForm.addEventListener('submit', function(e) {
        e.preventDefault();
        submitHealthMetric(this);
      });
    }

    // Medical record search
    const recordSearchInput = document.getElementById('record-search');
    if (recordSearchInput) {
      recordSearchInput.addEventListener('input', debounce(searchMedicalRecords, 300));
    }

    // Appointment cancellation
    const cancelButtons = document.querySelectorAll('.cancel-appointment-btn');
    cancelButtons.forEach(button => {
      button.addEventListener('click', function(e) {
        e.preventDefault();

        const appointmentId = this.dataset.appointmentId;
        const appointmentDate = this.dataset.appointmentDate || 'this appointment';

        if (confirm(`Are you sure you want to cancel ${appointmentDate}?`)) {
          cancelAppointment(appointmentId);
        }
      });
    });
  }

  /**
   * Update medication reminder settings
   */
  function updateMedicationReminder(medicationId, isEnabled) {
    // Get CSRF token
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

    // Send update request
    fetch(`/api/medications/${medicationId}/reminders/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify({ enabled: isEnabled })
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        // Show success message
        showNotification(`Medication reminders ${isEnabled ? 'enabled' : 'disabled'}`, 'success');
      } else {
        // Show error and reset toggle
        showNotification(data.message || 'Failed to update reminder settings', 'error');

        const toggle = document.querySelector(`.medication-reminder-toggle[data-medication-id="${medicationId}"]`);
        if (toggle) {
          toggle.checked = !isEnabled;
        }
      }
    })
    .catch(error => {
      console.error('Error updating medication reminder:', error);
      showNotification('An error occurred. Please try again.', 'error');

      // Reset toggle
      const toggle = document.querySelector(`.medication-reminder-toggle[data-medication-id="${medicationId}"]`);
      if (toggle) {
        toggle.checked = !isEnabled;
      }
    });
  }

  /**
   * Update available dates based on doctor's schedule
   */
  function updateAvailableDates(doctorId) {
    if (!doctorId) return;

    const appointmentCalendar = document.getElementById('appointment-calendar');
    if (!appointmentCalendar || typeof appointmentCalendar._flatpickr === 'undefined') return;

    // Show loading indicator
    appointmentCalendar.classList.add('opacity-50');

    // Get appointment type if applicable
    let appointmentType = '';
    const typeSelect = document.getElementById('appointment_type');
    if (typeSelect) {
      appointmentType = typeSelect.value;
    }

    // Get CSRF token
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

    // Fetch available dates
    fetch('/api/appointments/available-dates/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify({
        doctor_id: doctorId,
        appointment_type: appointmentType
      })
    })
    .then(response => response.json())
    .then(data => {
      // Update flatpickr with new disable dates
      if (data.unavailable_dates) {
        appointmentCalendar._flatpickr.set('disable', data.unavailable_dates);
      }

      // Remove loading indicator
      appointmentCalendar.classList.remove('opacity-50');
    })
    .catch(error => {
      console.error('Error fetching available dates:', error);
      appointmentCalendar.classList.remove('opacity-50');
      showNotification('Error loading available dates. Please try again.', 'error');
    });
  }

  /**
   * Submit health metric form data
   */
  function submitHealthMetric(form) {
    // Get form data
    const formData = new FormData(form);

    // Get CSRF token
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

    // Convert FormData to JSON
    const data = {};
    formData.forEach((value, key) => {
      data[key] = value;
    });

    // Send the data
    fetch('/api/health-metrics/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        // Show success message
        showNotification('Health metrics saved successfully', 'success');

        // Clear form
        form.reset();

        // Update chart if available
        updateHealthCharts();
      } else {
        // Show error message
        showNotification(data.message || 'Failed to save health metrics', 'error');
      }
    })
    .catch(error => {
      console.error('Error saving health metrics:', error);
      showNotification('An error occurred. Please try again.', 'error');
    });
  }

  /**
   * Update health charts with latest data
   */
  function updateHealthCharts() {
    // Only update if Chart.js is loaded
    if (typeof Chart === 'undefined') return;

    // Get CSRF token
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

    // Fetch latest health data
    fetch('/api/health-metrics/latest/', {
      headers: {
        'X-CSRFToken': csrfToken
      }
    })
    .then(response => response.json())
    .then(data => {
      // Update blood pressure chart
      const bpChart = Chart.getChart('blood-pressure-chart');
      if (bpChart && data.bp_data) {
        bpChart.data.labels = data.bp_data.labels;
        bpChart.data.datasets[0].data = data.bp_data.systolic;
        bpChart.data.datasets[1].data = data.bp_data.diastolic;
        bpChart.update();
      }

      // Update weight chart
      const weightChart = Chart.getChart('weight-chart');
      if (weightChart && data.weight_data) {
        weightChart.data.labels = data.weight_data.labels;
        weightChart.data.datasets[0].data = data.weight_data.data;
        weightChart.update();
      }

      // Update latest metrics display
      if (data.latest_metrics) {
        const latestMetrics = data.latest_metrics;

        // Update blood pressure display
        const bpDisplay = document.getElementById('latest-bp');
        if (bpDisplay && latestMetrics.systolic && latestMetrics.diastolic) {
          bpDisplay.textContent = `${latestMetrics.systolic}/${latestMetrics.diastolic}`;
        }

        // Update heart rate display
        const hrDisplay = document.getElementById('latest-hr');
        if (hrDisplay && latestMetrics.heart_rate) {
          hrDisplay.textContent = `${latestMetrics.heart_rate} bpm`;
        }

        // Update weight display
        const weightDisplay = document.getElementById('latest-weight');
        if (weightDisplay && latestMetrics.weight) {
          weightDisplay.textContent = `${latestMetrics.weight} kg`;
        }

        // Update temperature display
        const tempDisplay = document.getElementById('latest-temp');
        if (tempDisplay && latestMetrics.temperature) {
          tempDisplay.textContent = `${latestMetrics.temperature}°C`;
        }

        // Update metrics date
        const dateDisplay = document.getElementById('metrics-date');
        if (dateDisplay && latestMetrics.recorded_at) {
          const date = new Date(latestMetrics.recorded_at);
          dateDisplay.textContent = date.toLocaleDateString();
        }
      }
    })
    .catch(error => {
      console.error('Error updating health charts:', error);
    });
  }

  /**
   * Search medical records
   */
  function searchMedicalRecords() {
    const searchInput = document.getElementById('record-search');
    const searchTerm = searchInput.value.toLowerCase();
    const recordItems = document.querySelectorAll('.medical-record-item');

    let matchCount = 0;

    recordItems.forEach(item => {
      const recordType = item.dataset.recordType.toLowerCase();
      const doctorName = item.dataset.doctorName.toLowerCase();
      const recordDate = item.dataset.recordDate.toLowerCase();
      const recordContent = (item.dataset.recordContent || '').toLowerCase();

      if (recordType.includes(searchTerm) ||
          doctorName.includes(searchTerm) ||
          recordDate.includes(searchTerm) ||
          recordContent.includes(searchTerm)) {
        item.style.display = '';
        matchCount++;
      } else {
        item.style.display = 'none';
      }
    });

    // Update search results count
    const resultsCounter = document.getElementById('search-results-count');
    if (resultsCounter) {
      resultsCounter.textContent = matchCount;
      resultsCounter.parentElement.style.display = searchTerm ? '' : 'none';
    }
  }

  /**
   * Cancel an appointment
   */
  function cancelAppointment(appointmentId) {
    // Get CSRF token
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

    // Send cancellation request
    fetch(`/api/appointments/${appointmentId}/cancel/`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': csrfToken
      }
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        // Show success notification
        showNotification('Appointment cancelled successfully', 'success');

        // Update UI
        const appointmentElement = document.querySelector(`[data-appointment-id="${appointmentId}"]`).closest('.appointment-card');
        if (appointmentElement) {
          // Either remove the element or update its status
          if (data.remove_from_ui) {
            appointmentElement.remove();
          } else {
            const statusBadge = appointmentElement.querySelector('.status-badge');
            if (statusBadge) {
              statusBadge.className = 'status-badge px-2 py-1 text-xs font-medium rounded-full bg-red-100 text-red-800';
              statusBadge.textContent = 'Cancelled';
            }

            // Disable cancel button
            const cancelButton = appointmentElement.querySelector('.cancel-appointment-btn');
            if (cancelButton) {
              cancelButton.disabled = true;
              cancelButton.classList.add('opacity-50', 'cursor-not-allowed');
            }
          }
        }
      } else {
        // Show error notification
        showNotification(data.message || 'Failed to cancel appointment', 'error');
      }
    })
    .catch(error => {
      console.error('Error cancelling appointment:', error);
      showNotification('An error occurred. Please try again.', 'error');
    });
  }

  /**
   * Display a notification message
   */
  function showNotification(message, type = 'info') {
    // Check if notification container exists, create if not
    let notificationContainer = document.getElementById('notification-container');
    if (!notificationContainer) {
      notificationContainer = document.createElement('div');
      notificationContainer.id = 'notification-container';
      notificationContainer.className = 'fixed top-4 right-4 z-50 space-y-4';
      document.body.appendChild(notificationContainer);
    }

    // Create notification element
    const notification = document.createElement('div');
    notification.className = 'p-4 rounded-lg shadow-lg transform transition-all duration-300 translate-x-0 opacity-0 flex items-start';

    // Set style based on notification type
    if (type === 'success') {
      notification.classList.add('bg-green-50', 'text-green-800', 'border', 'border-green-200');
    } else if (type === 'error') {
      notification.classList.add('bg-red-50', 'text-red-800', 'border', 'border-red-200');
    } else if (type === 'warning') {
      notification.classList.add('bg-yellow-50', 'text-yellow-800', 'border', 'border-yellow-200');
    } else {
      notification.classList.add('bg-blue-50', 'text-blue-800', 'border', 'border-blue-200');
    }

    // Create icon based on type
    const iconWrapper = document.createElement('div');
    iconWrapper.className = 'flex-shrink-0 mr-3';

    let iconSvg = '';
    if (type === 'success') {
      iconSvg = '<svg class="h-5 w-5 text-green-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" /></svg>';
    } else if (type === 'error') {
      iconSvg = '<svg class="h-5 w-5 text-red-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" /></svg>';
    } else if (type === 'warning') {
      iconSvg = '<svg class="h-5 w-5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" /></svg>';
    } else {
      iconSvg = '<svg class="h-5 w-5 text-blue-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" /></svg>';
    }

    iconWrapper.innerHTML = iconSvg;

    // Create message content
    const contentWrapper = document.createElement('div');
    contentWrapper.className = 'flex-1';
    contentWrapper.textContent = message;

    // Create close button
    const closeButton = document.createElement('button');
    closeButton.className = 'ml-4 flex-shrink-0 h-5 w-5 text-gray-400 hover:text-gray-500 focus:outline-none';
    closeButton.innerHTML = '<svg class="h-5 w-5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" /></svg>';
    closeButton.addEventListener('click', () => {
      removeNotification(notification);
    });

    // Assemble notification
    notification.appendChild(iconWrapper);
    notification.appendChild(contentWrapper);
    notification.appendChild(closeButton);

    // Add to container
    notificationContainer.appendChild(notification);

    // Animate in
    setTimeout(() => {
      notification.classList.remove('translate-x-0', 'opacity-0');
      notification.classList.add('translate-x-0', 'opacity-100');
    }, 10);

    // Auto-remove after delay
    setTimeout(() => {
      removeNotification(notification);
    }, 5000);
  }

  /**
   * Remove a notification with animation
   */
  function removeNotification(notification) {
    notification.classList.remove('translate-x-0', 'opacity-100');
    notification.classList.add('translate-x-full', 'opacity-0');

    setTimeout(() => {
      notification.remove();
    }, 300);
  }

  /**
   * Debounce function to limit how often a function can be called
   */
  function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }

  /**
   * Equalize the heights of dashboard stat cards in each row
   */
  function equalizeCardHeights() {
    // Get all stat cards
    const cards = document.querySelectorAll('.stat-card');
    if (cards.length === 0) return;

    // Reset heights
    cards.forEach(card => {
      card.style.height = 'auto';
    });

    // Get the row groups (4 cards per row on large screens, 2 on medium, 1 on small)
    const viewportWidth = window.innerWidth;
    let cardsPerRow = 1;

    if (viewportWidth >= 1024) { // lg breakpoint
      cardsPerRow = 4;
    } else if (viewportWidth >= 640) { // sm breakpoint
      cardsPerRow = 2;
    }

    // Process each row
    for (let i = 0; i < cards.length; i += cardsPerRow) {
      const rowCards = Array.from(cards).slice(i, i + cardsPerRow);

      // Find tallest card in this row
      let maxHeight = 0;
      rowCards.forEach(card => {
        maxHeight = Math.max(maxHeight, card.offsetHeight);
      });

      // Set all cards in this row to the height of the tallest
      rowCards.forEach(card => {
        card.style.height = maxHeight + 'px';
      });
    }
  }

  /**
   * Adjust the dashboard container height dynamically based on viewport and content
   */
  function adjustDashboardHeight() {
  const dashboardContainer = document.querySelector('.bg-gray-50.min-h-screen');
  if (!dashboardContainer) return;

  // Get the viewport height
  const viewportHeight = window.innerHeight;

  // Get the footer and header heights
  const footer = document.querySelector('footer');
  const header = document.querySelector('.bg-white.shadow');

  if (!footer || !header) return;

  const footerHeight = footer.offsetHeight;
  const headerHeight = header.offsetHeight;

  // Calculate the exact height needed to fill the viewport
  const containerHeight = viewportHeight - footerHeight - headerHeight;

  // Set the exact height of the dashboard container
  dashboardContainer.style.height = `${containerHeight}px`;

  // Remove min-height to prevent conflicts
  dashboardContainer.style.minHeight = 'initial';
}

/**
 * Truncate document titles while preserving file extensions
 */
function truncateDocumentTitles() {
  // More aggressive truncation for better display
  const maxDisplayLength = 25;

  // Find all document titles - wait a bit for dynamic content
  setTimeout(() => {
    const documentTitles = document.querySelectorAll('.document-title');

    documentTitles.forEach(titleElement => {
      // Skip if already processed
      if (titleElement.hasAttribute('data-truncated')) {
        return;
      }

      const fullTitle = titleElement.textContent.trim();

      // Skip if title is already short enough
      if (fullTitle.length <= maxDisplayLength) {
        return;
      }

      // Store original title for tooltip
      titleElement.setAttribute('title', fullTitle);
      titleElement.setAttribute('data-truncated', 'true');
      titleElement.style.cursor = 'help';

      // Extract file extension
      const lastDotIndex = fullTitle.lastIndexOf('.');
      let extension = '';
      let nameWithoutExtension = fullTitle;

      if (lastDotIndex > -1 && lastDotIndex > fullTitle.length - 10) {
        extension = fullTitle.slice(lastDotIndex);
        nameWithoutExtension = fullTitle.slice(0, lastDotIndex);
      }

      // Special handling for TCGA file names
      if (nameWithoutExtension.startsWith('TCGA')) {
        // Extract just the TCGA identifier
        const parts = nameWithoutExtension.split(/[_.-]/);
        titleElement.textContent = parts[0] + '...' + extension;
      } else {
        // For other files, aggressive truncation
        const maxNameLength = maxDisplayLength - extension.length - 3; // -3 for "..."
        if (nameWithoutExtension.length > maxNameLength) {
          titleElement.textContent = nameWithoutExtension.slice(0, maxNameLength) + '...' + extension;
        } else {
          titleElement.textContent = fullTitle;
        }
      }
    });
  }, 100); // Small delay to ensure DOM is ready
}
});